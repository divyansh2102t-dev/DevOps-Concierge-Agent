import sys
import asyncio
import json
import os

# Force Windows ProactorEventLoop policy for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class FileStatusLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        
    def send(self, event_type, message, **kwargs):
        event = {"type": event_type, "message": message}
        event.update(kwargs)
        try:
            with open(self.log_path, "a", encoding="utf-8", buffering=1) as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

async def main():
    if len(sys.argv) < 2:
        print("Usage: python key_harvester_cli.py <log_file_path>")
        sys.exit(1)
        
    log_path = sys.argv[1]
    logger = FileStatusLogger(log_path)
    
    from backend.tools.key_harvester import harvest_keys_task
    try:
        await harvest_keys_task(logger)
    except Exception as e:
        logger.send("error", f"Fatal error in harvester process: {e}")

if __name__ == "__main__":
    asyncio.run(main())
