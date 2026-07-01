import uuid
import time
import os
import signal
import sys
from typing import Dict, Any, List, Optional

class TerminalSession:
    def __init__(self, command_id: str, command: str, working_dir: str):
        self.command_id = command_id
        self.command = command
        self.working_dir = working_dir
        self.status = "running"  # running, completed, error
        self.stdout = ""
        self.stderr = ""
        self.pid = None
        self.exit_code = None
        self.start_time = time.time()
        self.end_time = None
        self.process = None  # asyncio.subprocess.Process handle

class TerminalManager:
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.active_agents_list: List[Dict[str, Any]] = []

    def start_session(self, command: str, working_dir: str) -> str:
        cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
        session = TerminalSession(cmd_id, command, working_dir)
        self.sessions[cmd_id] = session
        return cmd_id

    def set_process(self, cmd_id: str, process):
        """Store the live subprocess handle so we can kill it on demand."""
        if cmd_id in self.sessions:
            self.sessions[cmd_id].process = process

    def update_session(self, cmd_id: str, pid: int = None, stdout_chunk: str = None, stderr_chunk: str = None):
        if cmd_id in self.sessions:
            session = self.sessions[cmd_id]
            if pid is not None:
                session.pid = pid
            if stdout_chunk is not None:
                session.stdout += stdout_chunk
            if stderr_chunk is not None:
                session.stderr += stderr_chunk

    def complete_session(self, cmd_id: str, exit_code: int, error: str = None):
        if cmd_id in self.sessions:
            session = self.sessions[cmd_id]
            session.status = "completed" if exit_code == 0 else "error"
            session.exit_code = exit_code
            session.process = None  # release handle
            if error:
                session.stderr += error
            session.end_time = time.time()

    def kill_session(self, cmd_id: str) -> bool:
        """Terminate a running process. Returns True if killed, False if not found/already done."""
        if cmd_id not in self.sessions:
            return False
        session = self.sessions[cmd_id]
        if session.status != "running":
            return False
        try:
            if session.process is not None:
                session.process.kill()
            elif session.pid:
                if sys.platform == "win32":
                    os.kill(session.pid, signal.SIGTERM)
                else:
                    os.killpg(os.getpgid(session.pid), signal.SIGTERM)
        except Exception:
            pass
        session.status = "error"
        session.stderr += "\n[Process terminated by user]"
        session.end_time = time.time()
        session.process = None
        return True

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        # Return sorted by start time (newest first)
        sorted_sessions = sorted(self.sessions.values(), key=lambda s: s.start_time, reverse=True)
        return [
            {
                "command_id": s.command_id,
                "command": s.command,
                "working_dir": s.working_dir,
                "status": s.status,
                "stdout": s.stdout,
                "stderr": s.stderr,
                "pid": s.pid,
                "exit_code": s.exit_code,
                "duration": round((s.end_time or time.time()) - s.start_time, 2),
                "killable": s.status == "running"
            }
            for s in sorted_sessions
        ]

    def set_active_agents(self, agents: List[Dict[str, Any]]):
        self.active_agents_list = agents

    def get_active_agents(self) -> List[Dict[str, Any]]:
        return self.active_agents_list

    def kill_all_active_sessions(self) -> bool:
        """Kills all currently running terminal sessions."""
        killed_any = False
        for cmd_id, session in list(self.sessions.items()):
            if session.status == "running":
                self.kill_session(cmd_id)
                killed_any = True
        return killed_any

    def clear_history(self):
        self.kill_all_active_sessions()
        self.sessions.clear()

# Global manager instance
manager = TerminalManager()
