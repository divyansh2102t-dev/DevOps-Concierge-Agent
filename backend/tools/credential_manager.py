import os
import re


def extract_env_vars(text):
    patterns = [
        r'([A-Z][A-Z0-9_]+)\s*[=:]\s*["\']?([^"\'\s\n]+)["\']?',
        r'(?:key|token|secret|password|api.?key)\s*[=:]\s*["\']?([^"\'\s\n]+)["\']?',
    ]

    env_vars = {}
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple) and len(match) == 2:
                key, value = match
                if len(value) > 4 and not value.startswith("http"):
                    env_vars[key] = value

    return env_vars


def generate_env_file(env_vars, project_dir):
    env_path = os.path.join(project_dir, ".env")
    gitignore_path = os.path.join(project_dir, ".gitignore")

    lines = []
    for key, value in env_vars.items():
        lines.append(f'{key}="{value}"')

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            content = f.read()
        if ".env" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n.env\n.env.local\n")
    else:
        with open(gitignore_path, "w") as f:
            f.write(".env\n.env.local\n")

    example_lines = [f'{key}=""' for key in env_vars.keys()]
    example_path = os.path.join(project_dir, ".env.example")
    with open(example_path, "w", encoding="utf-8") as f:
        f.write("\n".join(example_lines) + "\n")

    return {
        "success": True,
        "env_file": env_path,
        "variables": list(env_vars.keys()),
        "example_file": example_path
    }
