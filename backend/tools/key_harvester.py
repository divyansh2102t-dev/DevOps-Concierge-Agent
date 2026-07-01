import os
import json
import asyncio
import shutil
import random
import re
import uuid
from playwright.async_api import async_playwright
from backend.tools.url_parser import get_local_browser_profiles, clone_profile_safely
from backend.tools.key_store import set_key, get_key

# Global state to manage interactive billing approvals
pending_billing_approvals = {}

class KeyHarvesterStatus:
    """Helper class to yield step-by-step progress events back to the FastAPI SSE stream."""
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        
    def send(self, event_type: str, message: str, **kwargs):
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(
            self.queue.put_nowait,
            {"type": event_type, "message": message, **kwargs}
        )

async def harvest_keys_task(status_logger: KeyHarvesterStatus):
    """
    Core harvester task.
    1. Scans and clones local browser profiles (Chrome, Edge, Brave, Chrome Beta).
    2. Sequentially launches Playwright for each profile to harvest keys from logged-in consoles.
    3. Triggers billing safeguards if a paid account is detected.
    4. Saves discovered keys to the key store.
    """
    status_logger.send("progress", "Scanning local browser profiles on your machine...")
    profiles = get_local_browser_profiles()
    
    if not profiles:
        status_logger.send("error", "No browser profiles (Chrome, Edge, Brave, Chrome Beta) found. Please ensure a browser is installed.")
        return
        
    status_logger.send("progress", f"Found {len(profiles)} browser profiles: " + ", ".join([p["label"] for p in profiles]))
    
    # Generate unique suffix to prevent name conflicts
    suffix = "".join(random.choices("0123456789abcdef", k=4))
    
    # We will scan profiles to find active sessions
    for idx, profile in enumerate(profiles):
        status_logger.send("progress", f"🔄 [{idx+1}/{len(profiles)}] Scanning profile: {profile['label']}...")
        
        status_logger.send("progress", f"Cloning session database and decryption keys for {profile['label']}...")
        cloned_info = clone_profile_safely(profile)
        
        status_logger.send("progress", f"Launching sandboxed Playwright context for {profile['label']} (this may take up to 30 seconds as browser starts)...")
        
        async with async_playwright() as p:
            browser_type = p.chromium
            try:
                status_logger.send("progress", f"Starting headless Chromium instance for {profile['label']}...")
                context = await browser_type.launch_persistent_context(
                    user_data_dir=cloned_info["user_data_dir"],
                    headless=True,
                    timeout=40000,  # Explicit 40-second timeout to prevent silent hangs
                    args=[
                        f"--profile-directory={cloned_info['profile_directory']}",
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )
                status_logger.send("progress", f"Headless Chromium started successfully! Beginning scanning sequence...")
            except Exception as e:
                status_logger.send("progress", f"⚠️ Could not launch browser for {profile['label']}: {e}")
                # Clean up cloned profile
                try:
                    shutil.rmtree(cloned_info["user_data_dir"])
                except Exception:
                    pass
                continue
                
            try:
                # Run all harvesters on this context!
                # ── 1. GOOGLE AI STUDIO (GEMINI) ──
                await harvest_gemini(context, status_logger)
                
                # ── 2. GROQ CONSOLE ──
                await harvest_groq(context, suffix, status_logger)
                
                # ── 3. OPENAI PLATFORM ──
                await harvest_openai(context, suffix, status_logger)
                
                # ── 4. ANTHROPIC CONSOLE ──
                await harvest_anthropic(context, suffix, status_logger)
                
                # ── 5. GITHUB PERSONAL ACCESS TOKENS ──
                await harvest_github(context, suffix, status_logger)
                
                # ── 6. VERCEL TOKENS ──
                await harvest_vercel(context, suffix, status_logger)
                
            except Exception as e:
                status_logger.send("progress", f"⚠️ Error during scan of {profile['label']}: {e}")
            finally:
                await context.close()
                
        # Clean up cloned profile
        try:
            shutil.rmtree(cloned_info["user_data_dir"])
        except Exception:
            pass
            
    status_logger.send("done", "✨ Magic API Key Auto-Discovery completed successfully!")

async def check_billing_safeguard(provider: str, key_value: str, label: str, status_logger: KeyHarvesterStatus) -> bool:
    """
    Suspends harvester execution if active billing is detected, prompting the user for approval.
    Returns True if approved, False if skipped.
    """
    status_logger.send("billing_check", f"💳 Checking billing/pro status on {provider.upper()}...")
    
    # Trigger secondary consent modal on the frontend
    event = asyncio.Event()
    pending_billing_approvals[provider] = {
        "key": key_value,
        "provider": provider,
        "label": label,
        "event": event,
        "approved": False
    }
    
    status_logger.send("billing_consent_required", f"⚠️ Paid/Pro account detected for {provider.upper()}! Waiting for your consent to import paid key...", provider=provider)
    
    # Wait until the user responds via the /approve-billing endpoint
    await event.wait()
    
    consent = pending_billing_approvals[provider]
    approved = consent["approved"]
    
    # Clean up state
    del pending_billing_approvals[provider]
    
    if approved:
        status_logger.send("progress", f"✅ Consent granted. Importing paid {provider.upper()} key...")
        return True
    else:
        status_logger.send("progress", f"🚫 Consent denied. Safely skipped paid {provider.upper()} key.")
        return False

# ── OAUTH AUTOMATION UTILITIES ──

async def handle_oauth_redirection(page, status_logger: KeyHarvesterStatus, auth_idx=0):
    """
    Checks if the page is currently on a Google or GitHub OAuth consent/login page
    and automates the click-through using active browser sessions.
    """
    await asyncio.sleep(4)
    url = page.url
    
    # ── Google OAuth Redirection ──
    if "accounts.google.com" in url:
        # Check if we are on the Account Chooser
        accounts = await page.locator('div[role="link"]').all()
        email_accounts = []
        for acc in accounts:
            text = await acc.inner_text()
            if "@" in text:
                email_accounts.append(acc)
                
        if email_accounts:
            click_idx = min(auth_idx, len(email_accounts) - 1)
            status_logger.send("progress", f"OAuth: Selecting Google Account index {click_idx} in chooser...")
            await email_accounts[click_idx].click()
            await asyncio.sleep(6)
            
        # Check for consent screen / "Continue" / "Allow" / "Confirm"
        for _ in range(2):
            consent_btn = page.locator('button:has-text("Continue"), button:has-text("Allow"), button:has-text("Confirm")')
            if await consent_btn.is_visible():
                status_logger.send("progress", "OAuth: Clicking Google consent confirmation...")
                await consent_btn.click()
                await asyncio.sleep(5)
                
    # ── GitHub OAuth Redirection ──
    elif "github.com/login/oauth" in url or "github.com/login" in url:
        # If GitHub asks to authorize the app:
        authorize_btn = page.locator('button[id="js-oauth-authorize-btn"], button:has-text("Authorize")')
        if await authorize_btn.is_visible():
            status_logger.send("progress", "OAuth: Clicking GitHub application authorization...")
            await authorize_btn.click()
            await asyncio.sleep(6)

async def attempt_oauth_login(page, status_logger: KeyHarvesterStatus) -> bool:
    """
    Attempts to click the 'Continue with Google' or 'Continue with GitHub' OAuth buttons
    on the login page of a platform, and then handles the redirection.
    """
    await asyncio.sleep(3)
    
    # Check for Google Login Button
    google_btn = page.locator('button:has-text("Continue with Google"), button:has-text("Sign in with Google"), button:has-text("Google"), a:has-text("Google")').first
    
    # Check for GitHub Login Button
    github_btn = page.locator('button:has-text("Continue with GitHub"), button:has-text("Sign in with GitHub"), button:has-text("GitHub"), a:has-text("GitHub")').first
    
    if await google_btn.is_visible():
        status_logger.send("progress", "Login screen detected. Automating 'Continue with Google' OAuth sign-in...")
        await google_btn.click()
        await handle_oauth_redirection(page, status_logger)
        return True
        
    elif await github_btn.is_visible():
        status_logger.send("progress", "Login screen detected. Automating 'Continue with GitHub' OAuth sign-in...")
        await github_btn.click()
        await handle_oauth_redirection(page, status_logger)
        return True
        
    return False

# ── PROVIDER-SPECIFIC HARVESTERS ──

async def harvest_gemini(context, status_logger: KeyHarvesterStatus):
    """
    Scrapes Google AI Studio. 
    Supports Google OAuth sign-in automation and multi-account scanning (authuser=0, 1, 2...)
    to harvest multiple free keys from all logged-in Google accounts on the profile.
    """
    status_logger.send("progress", "Navigating to Google AI Studio to check for active Google sessions...")
    
    # Scan up to 5 logged-in Google accounts using authuser query parameter
    for auth_idx in range(5):
        page = await context.new_page()
        try:
            url = f"https://aistudio.google.com/app/apikey?authuser={auth_idx}"
            await page.goto(url, timeout=10000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # ── Step 1: Automate Google OAuth Login / Account Chooser ──
            if "accounts.google.com" in page.url or "signin" in page.url:
                # Find active signed-in accounts in Google's chooser
                accounts = await page.locator('div[role="link"]').all()
                email_accounts = []
                for acc in accounts:
                    text = await acc.inner_text()
                    if "@" in text:
                        email_accounts.append(acc)
                        
                if auth_idx < len(email_accounts):
                    status_logger.send("progress", f"Found active Google session {auth_idx}. Automating OAuth login...")
                    await email_accounts[auth_idx].click()
                    await asyncio.sleep(6)
                else:
                    # No more active accounts signed into Google in this profile
                    if auth_idx > 0:
                        status_logger.send("progress", f"No further active Google accounts found in this profile.")
                    else:
                        status_logger.send("progress", "⚠️ No logged-in Google account found. Please sign into Google in your browser.")
                    await page.close()
                    break
                    
            # ── Step 2: Automate Consent/Confirm screens ──
            # Click "Continue" / "Confirm" / "Allow" if Google prompts for app authorization
            for _ in range(2):
                consent_btn = page.locator('button:has-text("Continue"), button:has-text("Allow"), button:has-text("Confirm")')
                if await consent_btn.is_visible():
                    status_logger.send("progress", "Automating Google OAuth authorization consent...")
                    await consent_btn.click()
                    await asyncio.sleep(5)
                    
            # ── Step 3: Automate AI Studio Terms of Service Onboarding ──
            # If a new account logs in, Google AI Studio presents a Terms of Service modal with checkboxes
            checkboxes = await page.locator('input[type="checkbox"]').all()
            if checkboxes:
                status_logger.send("progress", "Accepting Google AI Studio Terms of Service automatically...")
                for cb in checkboxes:
                    try:
                        await cb.check()
                    except Exception:
                        pass
                accept_btn = page.locator('button:has-text("Accept"), button:has-text("Agree"), button:has-text("I agree"), button:has-text("Continue")')
                if await accept_btn.is_visible():
                    await accept_btn.click()
                    await asyncio.sleep(5)
                    
            # ── Step 4: Verify Successful Landing on API Key Page ──
            content = await page.content()
            if "sign in" in content.lower() or "google account" in content.lower() or "accounts.google.com" in page.url:
                status_logger.send("progress", f"Account index {auth_idx} is not signed in or requires manual verification. Skipping.")
                await page.close()
                continue
                
            # ── Step 5: Extract or Create Key ──
            is_paid = "pay-as-you-go" in content.lower() or "billing" in content.lower() or "tier: pay" in content.lower()
            
            keys_found = re.findall(r"AIzaSy[A-Za-z0-9_\-]{33}", content)
            extracted_key = None
            
            if keys_found:
                extracted_key = keys_found[0]
                status_logger.send("progress", f"Found existing Gemini API Key for account index {auth_idx}!")
            else:
                status_logger.send("progress", f"No existing key found for account index {auth_idx}. Creating new key...")
                create_btn = page.get_by_role("button", name="Create API key").first
                if await create_btn.is_visible():
                    await create_btn.click()
                    await asyncio.sleep(3)
                    
                    new_proj_btn = page.get_by_text("Create API key in new project")
                    if await new_proj_btn.is_visible():
                        await new_proj_btn.click()
                        await asyncio.sleep(6)
                    
                    new_content = await page.content()
                    keys_found = re.findall(r"AIzaSy[A-Za-z0-9_\-]{33}", new_content)
                    if keys_found:
                        extracted_key = keys_found[0]
                        status_logger.send("progress", f"Successfully created new Gemini API Key for account index {auth_idx}!")
                        
            if extracted_key:
                should_save = True
                if is_paid:
                    should_save = await check_billing_safeguard(f"gemini_{auth_idx}", extracted_key, f"Gemini Paid Account {auth_idx}", status_logger)
                    
                if should_save:
                    # Save first key as primary, subsequent keys go directly to the failover queue!
                    if auth_idx == 0 and not get_key("GEMINI_API_KEY"):
                        set_key("GEMINI_API_KEY", extracted_key)
                        status_logger.send("progress", f"✨ Gemini API Key (Account {auth_idx}) successfully saved as Primary Key!")
                    else:
                        await add_to_queue_store("gemini", f"Gemini Free-Discover-{auth_idx}", extracted_key)
                        status_logger.send("progress", f"✨ Gemini API Key (Account {auth_idx}) successfully added to your Failover Queue!")
            else:
                status_logger.send("progress", f"ℹ️ No Gemini API Key could be extracted or created for account index {auth_idx}.")
                
        except Exception as e:
            status_logger.send("progress", f"ℹ️ Gemini account index {auth_idx} check bypassed: {e}")
        finally:
            await page.close()

async def harvest_groq(context, suffix: str, status_logger: KeyHarvesterStatus):
    status_logger.send("progress", "Navigating to Groq Console...")
    page = await context.new_page()
    try:
        await page.goto("https://console.groq.com/keys", timeout=10000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        content = await page.content()
        # Automate OAuth Sign-in if login screen is detected
        if "sign in" in content.lower() or "login" in content.lower() or "signin" in page.url or "login" in page.url:
            await attempt_oauth_login(page, status_logger)
            await asyncio.sleep(5)
            content = await page.content()
            
        if "sign in" in content.lower() or "login" in content.lower() or "signin" in page.url or "login" in page.url:
            status_logger.send("progress", "⚠️ Not logged into Groq Console. Bypassing Groq.")
            await page.close()
            return
            
        is_paid = "payment method" in content.lower() or "card details" in content.lower()
        
        create_btn = page.get_by_role("button", name="Create API Key")
        if not await create_btn.is_visible():
            create_btn = page.get_by_text("Create API Key")
            
        if await create_btn.is_visible():
            await create_btn.click()
            await asyncio.sleep(2)
            
            input_name = page.locator("input[placeholder*='Key name']").first
            if not await input_name.is_visible():
                input_name = page.locator("input[type='text']").first
                
            if await input_name.is_visible():
                await input_name.fill(f"DevOps-Concierge-Auto-{suffix}")
                await asyncio.sleep(1)
                
            submit_btn = page.get_by_role("button", name="Create")
            if await submit_btn.is_visible():
                await submit_btn.click()
                await asyncio.sleep(3)
                
            modal_content = await page.content()
            groq_keys = re.findall(r"gsk_[A-Za-z0-9]{48}", modal_content)
            
            if groq_keys:
                extracted_key = groq_keys[0]
                status_logger.send("progress", "Created new Groq API Key!")
                
                should_save = True
                if is_paid:
                    should_save = await check_billing_safeguard("groq", extracted_key, "Groq Paid Auto-Discover", status_logger)
                    
                if should_save:
                    await add_to_queue_store("groq", f"Groq Auto-Discover-{suffix}", extracted_key)
                    status_logger.send("progress", "✨ Groq API Key successfully imported!")
            else:
                status_logger.send("progress", "ℹ️ Groq Key creation modal did not yield a key.")
        else:
            status_logger.send("progress", "ℹ️ Could not find 'Create API Key' button in Groq Console.")
            
    except Exception as e:
        status_logger.send("progress", f"ℹ️ Groq Console check bypassed: {e}")
    finally:
        await page.close()

async def harvest_openai(context, suffix: str, status_logger: KeyHarvesterStatus):
    status_logger.send("progress", "Navigating to OpenAI Platform...")
    page = await context.new_page()
    try:
        await page.goto("https://platform.openai.com/api-keys", timeout=10000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        content = await page.content()
        # Automate OAuth Sign-in if login screen is detected
        if "log in" in content.lower() or "sign up" in content.lower() or "login" in page.url or "signin" in page.url:
            await attempt_oauth_login(page, status_logger)
            await asyncio.sleep(5)
            content = await page.content()
            
        if "log in" in content.lower() or "sign up" in content.lower() or "login" in page.url or "signin" in page.url:
            status_logger.send("progress", "⚠️ Not logged into OpenAI Platform. Bypassing OpenAI.")
            await page.close()
            return
            
        status_logger.send("progress", "Checking OpenAI billing plan...")
        is_paid = False
        try:
            billing_page = await context.new_page()
            await billing_page.goto("https://platform.openai.com/settings/organization/billing/overview", timeout=8000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            billing_content = await billing_page.content()
            if "credit card" in billing_content.lower() or "payment method" in billing_content.lower() or "pay-as-you-go" in billing_content.lower():
                is_paid = True
            await billing_page.close()
        except Exception:
            pass
            
        create_btn = page.get_by_role("button", name="Create new secret key")
        if not await create_btn.is_visible():
            create_btn = page.get_by_text("Create new secret key")
            
        if await create_btn.is_visible():
            await create_btn.click()
            await asyncio.sleep(2)
            
            input_name = page.locator("input[placeholder*='name']").first
            if await input_name.is_visible():
                await input_name.fill(f"DevOps-Concierge-Auto-{suffix}")
                await asyncio.sleep(1)
                
            submit_btn = page.get_by_role("button", name="Create secret key")
            if await submit_btn.is_visible():
                await submit_btn.click()
                await asyncio.sleep(3)
                
            modal_content = await page.content()
            openai_keys = re.findall(r"sk-[A-Za-z0-9]{48}", modal_content)
            if not openai_keys:
                openai_keys = re.findall(r"sk-proj-[A-Za-z0-9_\-]{80,120}", modal_content)
                
            if openai_keys:
                extracted_key = openai_keys[0]
                status_logger.send("progress", "Created new OpenAI Secret Key!")
                
                should_save = True
                if is_paid:
                    should_save = await check_billing_safeguard("openai", extracted_key, "OpenAI Paid Auto-Discover", status_logger)
                    
                if should_save:
                    await add_to_queue_store("openai", f"OpenAI Auto-Discover-{suffix}", extracted_key)
                    status_logger.send("progress", "✨ OpenAI API Key successfully imported!")
            else:
                status_logger.send("progress", "ℹ️ OpenAI Key creation modal did not yield a key.")
        else:
            status_logger.send("progress", "ℹ️ Could not find 'Create secret key' button on OpenAI Platform.")
            
    except Exception as e:
        status_logger.send("progress", f"ℹ️ OpenAI Platform check bypassed: {e}")
    finally:
        await page.close()

async def harvest_anthropic(context, suffix: str, status_logger: KeyHarvesterStatus):
    status_logger.send("progress", "Navigating to Anthropic Console...")
    page = await context.new_page()
    try:
        await page.goto("https://console.anthropic.com/settings/keys", timeout=10000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        content = await page.content()
        # Automate OAuth Sign-in if login screen is detected
        if "login" in content.lower() or "sign in" in content.lower() or "login" in page.url or "signin" in page.url:
            await attempt_oauth_login(page, status_logger)
            await asyncio.sleep(5)
            content = await page.content()
            
        if "login" in content.lower() or "sign in" in content.lower() or "login" in page.url or "signin" in page.url:
            status_logger.send("progress", "⚠️ Not logged into Anthropic Console. Bypassing Anthropic.")
            await page.close()
            return
            
        status_logger.send("progress", "Checking Anthropic billing plan...")
        is_paid = False
        try:
            billing_page = await context.new_page()
            await billing_page.goto("https://console.anthropic.com/settings/plans", timeout=8000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            billing_content = await billing_page.content()
            if "active card" in billing_content.lower() or "credit balance" in billing_content.lower() or "commercial" in billing_content.lower():
                is_paid = True
            await billing_page.close()
        except Exception:
            pass
            
        create_btn = page.get_by_role("button", name="Create Key")
        if not await create_btn.is_visible():
            create_btn = page.get_by_text("Create Key")
            
        if await create_btn.is_visible():
            await create_btn.click()
            await asyncio.sleep(2)
            
            input_name = page.locator("input[type='text']").first
            if await input_name.is_visible():
                await input_name.fill(f"DevOps-Concierge-Auto-{suffix}")
                await asyncio.sleep(1)
                
            submit_btn = page.get_by_role("button", name="Create Key")
            if await submit_btn.is_visible():
                await submit_btn.click()
                await asyncio.sleep(3)
                
            modal_content = await page.content()
            anth_keys = re.findall(r"sk-ant-sid01-[A-Za-z0-9_\-]{60,100}", modal_content)
            if not anth_keys:
                anth_keys = re.findall(r"sk-ant-[A-Za-z0-9_\-]{80,120}", modal_content)
                
            if anth_keys:
                extracted_key = anth_keys[0]
                status_logger.send("progress", "Created new Anthropic Secret Key!")
                
                should_save = True
                if is_paid:
                    should_save = await check_billing_safeguard("anthropic", extracted_key, "Anthropic Paid Auto-Discover", status_logger)
                    
                if should_save:
                    await add_to_queue_store("anthropic", f"Anthropic Auto-Discover-{suffix}", extracted_key)
                    status_logger.send("progress", "✨ Anthropic API Key successfully imported!")
            else:
                status_logger.send("progress", "ℹ️ Anthropic Key creation modal did not yield a key.")
        else:
            status_logger.send("progress", "ℹ️ Could not find 'Create Key' button in Anthropic Console.")
            
    except Exception as e:
        status_logger.send("progress", f"ℹ️ Anthropic Console check bypassed: {e}")
    finally:
        await page.close()

async def harvest_github(context, suffix: str, status_logger: KeyHarvesterStatus):
    status_logger.send("progress", "Navigating to GitHub Personal Access Tokens...")
    page = await context.new_page()
    try:
        await page.goto("https://github.com/settings/tokens/new", timeout=10000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        content = await page.content()
        url = page.url
        if "login" in url or "session" in url or "Sign in to GitHub" in content:
            status_logger.send("progress", "⚠️ Not logged into GitHub. Please log in first so we can auto-discover your key!")
            await page.close()
            return
            
        if "sudo" in url or "confirm password" in content.lower():
            status_logger.send("progress", "⚠️ GitHub requires password confirmation (Sudo Mode) to generate a token. Skipping auto-discovery. Please generate a classic token manually at https://github.com/settings/tokens/new with 'repo' and 'workflow' scopes.")
            await page.close()
            return
            
        status_logger.send("progress", "Filling GitHub Classic Token generation form...")
        
        # Fill note name
        note_input = page.locator('input[id="oauth_access_token_note"]')
        if not await note_input.is_visible():
            note_input = page.locator('input[name*="note"]').first
        if await note_input.is_visible():
            await note_input.fill(f"DevOps-Concierge-Auto-{suffix}")
            await asyncio.sleep(1)
            
        # Select Scopes: 'repo' and 'workflow'
        repo_cb = page.locator('input[value="repo"]')
        if await repo_cb.is_visible():
            await repo_cb.check()
            await asyncio.sleep(0.5)
            
        workflow_cb = page.locator('input[value="workflow"]')
        if await workflow_cb.is_visible():
            await workflow_cb.check()
            await asyncio.sleep(0.5)
            
        # Click Generate token button
        gen_btn = page.locator('button:has-text("Generate token")')
        if not await gen_btn.is_visible():
            gen_btn = page.locator('button[type="submit"]:has-text("Generate")')
            
        if await gen_btn.is_visible():
            await gen_btn.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(3)
            
            # Extract key
            new_content = await page.content()
            gh_keys = re.findall(r"ghp_[A-Za-z0-9_]{36,80}", new_content)
            if not gh_keys:
                gh_keys = re.findall(r"github_pat_[A-Za-z0-9_]{82}", new_content)
                
            if gh_keys:
                extracted_key = gh_keys[0]
                set_key("GITHUB_TOKEN", extracted_key)
                status_logger.send("progress", "✨ GitHub API Token successfully imported!")
            else:
                status_logger.send("progress", "⚠️ GitHub token was generated, but the value could not be read from the success page. Please copy it manually.")
        else:
            status_logger.send("progress", "ℹ️ Could not find 'Generate token' button on GitHub page.")
            
    except Exception as e:
        status_logger.send("progress", f"ℹ️ GitHub check bypassed: {e}")
    finally:
        await page.close()

async def harvest_vercel(context, suffix: str, status_logger: KeyHarvesterStatus):
    status_logger.send("progress", "Navigating to Vercel Tokens...")
    page = await context.new_page()
    try:
        await page.goto("https://vercel.com/account/tokens", timeout=10000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        content = await page.content()
        url = page.url
        # Automate OAuth Sign-in if login screen is detected
        if "login" in url or "Log in to Vercel" in content or "signup" in url or "signin" in url:
            await attempt_oauth_login(page, status_logger)
            await asyncio.sleep(5)
            content = await page.content()
            url = page.url
            
        if "login" in url or "Log in to Vercel" in content or "signup" in url or "signin" in url:
            status_logger.send("progress", "⚠️ Not logged into Vercel. Bypassing Vercel.")
            await page.close()
            return
            
        status_logger.send("progress", "Creating Vercel Auto-Discovery Token...")
        
        # Look for Create/Create Token button
        create_btn = page.get_by_role("button", name="Create").first
        if not await create_btn.is_visible():
            create_btn = page.get_by_text("Create Token").first
            
        if await create_btn.is_visible():
            await create_btn.click()
            await asyncio.sleep(2)
            
            # Fill Name
            input_name = page.locator("input[placeholder*='Token Name']").first
            if not await input_name.is_visible():
                input_name = page.locator("input[type='text']").first
            if await input_name.is_visible():
                await input_name.fill(f"DevOps-Concierge-Auto-{suffix}")
                await asyncio.sleep(1)
                
            # Click Create/Submit button inside modal
            submit_btn = page.locator("button[type='submit']").first
            if not await submit_btn.is_visible():
                submit_btn = page.get_by_role("button", name="Create").last
            if await submit_btn.is_visible():
                await submit_btn.click()
                await asyncio.sleep(3)
                
                # Check all inputs for token value (alphanumeric 24-chars or starts with vc_)
                inputs = await page.locator("input").all()
                extracted_key = None
                for inp in inputs:
                    val = await inp.get_attribute("value")
                    if val and (len(val) == 24 or val.startswith("vc_")):
                        extracted_key = val
                        break
                        
                if not extracted_key:
                    # Fallback to text scanning
                    modal_content = await page.content()
                    tokens = re.findall(r"\b[A-Za-z0-9]{24}\b", modal_content)
                    if tokens:
                        for t in tokens:
                            if t.lower() not in ["default", "projects", "settings", "feedback", "security"]:
                                extracted_key = t
                                break
                                
                if extracted_key:
                    set_key("VERCEL_TOKEN", extracted_key)
                    status_logger.send("progress", "✨ Vercel API Token successfully imported!")
                else:
                    status_logger.send("progress", "⚠️ Vercel token was created, but the value could not be read from the modal. Please copy it manually.")
        else:
            status_logger.send("progress", "ℹ️ Could not find 'Create' or 'Create Token' button on Vercel page.")
            
    except Exception as e:
        status_logger.send("progress", f"ℹ️ Vercel check bypassed: {e}")
    finally:
        await page.close()

# ── STORAGE UTILITIES ──

async def add_to_queue_store(provider: str, label: str, value: str):
    """Saves a key to the key failover queue list in the key store."""
    queue_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(queue_val)
    except Exception:
        queue = []
        
    if any(item.get("value") == value for item in queue):
        return
        
    new_key_id = str(uuid.uuid4())
    
    queue.append({
        "id": new_key_id,
        "provider": provider,
        "label": label,
        "value": value
    })
    
    set_key("API_KEYS_QUEUE", json.dumps(queue))
