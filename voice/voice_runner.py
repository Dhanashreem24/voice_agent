import asyncio
import sys
import os
import uuid
import traceback
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

# Suppress logging
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from voice.stt import speech_to_text
from voice.tts import speak
from agents.root_agent import root_agent

# ---------------------------------------------------------
# THE COMPLETE ADK 1.21.0 COMPATIBILITY INTERFACE
# ---------------------------------------------------------

@dataclass
class MockRunConfig:
    # --- KNOWN FLAGS ---
    response_modalities: List[str] = field(default_factory=lambda: ["text"])
    speech_config: Any = None
    output_audio_transcription: bool = False
    input_audio_transcription: Any = None 
    realtime_input_config: Any = None
    enable_affective_dialog: bool = False
    proactivity: Any = None
    session_resumption: bool = False
    context_window_compression: Any = None
    
    # Common settings
    candidate_count: int = 1
    temperature: float = 0.7
    trace_context: Any = None
    user_id: str = "default_user"
    safety_settings: Any = None
    tool_config: Any = None

    # --- SAFETY NET ---
    # If the library asks for any other config flag, return None instead of crashing
    def __getattr__(self, name):
        return None

@dataclass
class MockSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Any] = field(default_factory=list)
    user: Any = None
    created_time: Any = None
    expiration_time: Any = None

    # --- SAFETY NET ---
    def __getattr__(self, name):
        return None

class MockPluginManager:
    async def run_before_agent_callback(self, *args, **kwargs): return None
    async def run_after_agent_callback(self, *args, **kwargs): return None

@dataclass
class ADKInvocationContext:
    history: List[Dict[str, str]]
    session: MockSession = field(default_factory=MockSession)
    plugin_manager: MockPluginManager = field(default_factory=MockPluginManager)
    run_config: MockRunConfig = field(default_factory=MockRunConfig)
    agent: Any = None
    end_invocation: bool = False 
    agent_states: Dict[str, Any] = field(default_factory=dict)
    
    # --- KNOWN CONTEXT ATTRIBUTES ---
    context_cache_config: Any = None
    trace_context: Any = None
    branch: Any = None
    
    # [FIX] Added specifically for your current error
    is_resumable: bool = False 

    def _get_events(self, **kwargs):
        """Returns session events, accepting any filter arguments."""
        return self.session.events

    # --- SAFETY NET ---
    # If the library asks for other context attributes, return None instead of crashing
    def __getattr__(self, name):
        return None

    def model_copy(self, update: Dict[str, Any] = None):
        # We manually copy known fields to ensure they persist
        new_ctx = ADKInvocationContext(
            history=list(self.history), 
            session=self.session,
            plugin_manager=self.plugin_manager,
            run_config=self.run_config,
            end_invocation=self.end_invocation,
            agent_states=self.agent_states,
            branch=self.branch,
            context_cache_config=self.context_cache_config,
            trace_context=self.trace_context,
            is_resumable=self.is_resumable
        )
        if update:
            for key, value in update.items():
                setattr(new_ctx, key, value)
        return new_ctx

    def model_dump(self):
        return asdict(self)

# ---------------------------------------------------------
# RUNNER
# ---------------------------------------------------------

async def run_voice_agent():
    print("\n" + "="*30)
    print("VOICE AGENT CONNECTED")
    print("="*30)

    await asyncio.to_thread(speak, "I'm ready. How can I help?")

    session_history = []

    while True:
        print("\n[Listening...]")
        user_text = await asyncio.to_thread(speech_to_text)

        if not user_text or not user_text.strip():
            continue

        print(f"User: {user_text}")
        session_history.append({"role": "user", "content": user_text})

        try:
            # Create fresh context for each turn
            context = ADKInvocationContext(history=session_history)

            print(f"Routing through: {root_agent.name}...")
            full_response = ""

            async for event in root_agent.run_async(context):
                if hasattr(event, "text"):
                    full_response += event.text
                elif hasattr(event, "delta") and hasattr(event.delta, "text"):
                    full_response += event.delta.text
                elif isinstance(event, str):
                    full_response += event

            if full_response:
                print(f"Agent Response: {full_response}")
                session_history.append({"role": "assistant", "content": full_response})
                await asyncio.to_thread(speak, full_response)
            else:
                print("No response from agent. Ensure sub-agents are correctly connected.")

        except Exception as e:
            print(f"!!! Error in Agent Loop: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(run_voice_agent())
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)