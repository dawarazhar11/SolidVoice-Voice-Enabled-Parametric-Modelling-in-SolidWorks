import configparser
import tempfile
import os

import anthropic
from faster_whisper import WhisperModel
import speech_recognition as sr

from pySldWrap import sw_tools
from part_memory import PartMemory

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
config = configparser.ConfigParser()
config.read("config.ini")

anthropic_api_key = config["ANTHROPIC"]["API_KEY"]
anthropic_base_url = config.get("ANTHROPIC", "BASE_URL", fallback="").strip()
sw_version = config.get("SOLIDWORKS", "VERSION", fallback="2025")
whisper_model_size = config.get("WHISPER", "MODEL_SIZE", fallback="base")
qdrant_url = config.get("QDRANT", "URL", fallback="http://localhost:6333")
ollama_url = config.get("OLLAMA", "URL", fallback="http://localhost:11434")

# Anthropic Claude client (for sketch reasoning / command interpretation)
# Supports direct Anthropic API or proxies like sub2api via BASE_URL
client_kwargs = {"api_key": anthropic_api_key}
if anthropic_base_url:
    client_kwargs["base_url"] = anthropic_base_url
    print(f"Using custom Anthropic base URL: {anthropic_base_url}")
claude_client = anthropic.Anthropic(**client_kwargs)

# Local Whisper model for speech-to-text (runs entirely on device)
print(f"Loading local Whisper model ({whisper_model_size})...")
whisper_model = WhisperModel(whisper_model_size, device="auto", compute_type="auto")
print("Whisper model loaded.")

# ---------------------------------------------------------------------------
# SolidWorks connection
# ---------------------------------------------------------------------------
sw_tools.connect_sw(sw_version)


# ---------------------------------------------------------------------------
# AI helpers
# ---------------------------------------------------------------------------
CLAUDE_MODEL = config.get("ANTHROPIC", "MODEL", fallback="claude-sonnet-4-20250514")


def get_claude_response(prompt, system=None):
    """Send a prompt to Claude and return the text response."""
    kwargs = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    message = claude_client.messages.create(**kwargs)
    return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# Speech-to-text using local Whisper (faster-whisper)
# ---------------------------------------------------------------------------
def recognize_speech():
    """Record audio from the microphone and transcribe it locally with Whisper."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for your command...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source)

    # Write captured audio to a temporary WAV file for local Whisper
    wav_data = audio.get_wav_data()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        tmp.write(wav_data)
        tmp.close()

        segments, _info = whisper_model.transcribe(tmp.name, beam_size=5)
        text = " ".join(segment.text for segment in segments).strip()

        if text:
            print(f"You said: {text}")
            return text
        else:
            print("Could not understand audio.")
            return None
    except Exception as e:
        print(f"Speech recognition error: {e}")
        return None
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Feature labeling – ask Claude to generate a descriptive label
# ---------------------------------------------------------------------------
def generate_feature_label(feature_type, user_intent, params, context_summary=""):
    """Ask Claude to produce a short, descriptive label for a SolidWorks feature."""
    prompt = (
        "You are a SolidWorks feature naming assistant.\n"
        f"Feature type: {feature_type}\n"
        f"User's voice command: \"{user_intent}\"\n"
        f"Parameters: {params}\n"
    )
    if context_summary:
        prompt += f"\nExisting part history:\n{context_summary}\n"
    prompt += (
        "\nGenerate a short (2-5 word) descriptive label for this feature that "
        "would make sense in a SolidWorks feature tree. "
        "Respond with ONLY the label, nothing else.\n"
        "Examples: 'Base Plate Sketch', 'Main Body Extrude', 'Edge Fillet 5mm'"
    )
    return get_claude_response(prompt)


def rename_sw_feature(model, old_name, new_label):
    """Rename a SolidWorks feature in the feature tree."""
    try:
        import win32com.client
        import pythoncom
        arg1 = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        selected = model.Extension.SelectByID2(
            old_name, "BODYFEATURE", 0, 0, 0, False, 0, arg1, 0
        )
        if selected:
            feat = model.SelectionManager.GetSelectedObject6(1, -1)
            if feat:
                feat.Name = new_label
                print(f"Renamed feature '{old_name}' -> '{new_label}'")
                return True
    except Exception as e:
        print(f"Could not rename feature: {e}")
    return False


# ---------------------------------------------------------------------------
# Sketch creation
# ---------------------------------------------------------------------------
def parse_sketch_command(user_command):
    """Use Claude to interpret a voice command and return structured sketch info."""
    prompt = (
        "You are a SolidWorks automation assistant. "
        "The user said the following command about creating a sketch:\n\n"
        f'"{user_command}"\n\n'
        "Respond with ONLY one of these sketch types on the first line: "
        "rectangle, circle, line, arc, polygon\n"
        "On the second line provide comma-separated numeric parameters "
        "(coordinates and dimensions in metres). "
        "For a rectangle: x1,y1,x2,y2  "
        "For a circle: cx,cy,radius  "
        "For a line: x1,y1,x2,y2  "
        "If the user did not specify dimensions, use sensible defaults."
    )
    return get_claude_response(prompt)


def create_sketch(sketch_type, *args):
    """Create a sketch in SolidWorks via pySldWrap."""
    instruction = get_claude_response(
        f"Give a brief explanation of how to create a {sketch_type} sketch "
        "in SOLIDWORKS using the Python COM API (pywin32). Keep it under 3 sentences."
    )
    print("Instruction:", instruction)

    model = sw_tools.sw.app.NewDocument("Part", 0, 0, 0)
    model.SketchManager.InsertSketch(True)

    if sketch_type == "rectangle":
        x1, y1, x2, y2 = (args + (0, 0, 0.1, 0.1))[0:4]
        model.SketchManager.CreateCornerRectangle(x1, y1, 0, x2, y2, 0)
    elif sketch_type == "circle":
        cx, cy, r = (args + (0, 0, 0.05))[0:3]
        model.SketchManager.CreateCircle(cx, cy, 0, cx + r, cy, 0)
    elif sketch_type == "line":
        x1, y1, x2, y2 = (args + (0, 0, 0.1, 0.1))[0:4]
        model.SketchManager.CreateLine(x1, y1, 0, x2, y2, 0)
    else:
        print(f"Sketch type '{sketch_type}' is not yet automated. "
              "Creating a default rectangle.")
        model.SketchManager.CreateCornerRectangle(0, 0, 0, 0.1, 0.1, 0)

    model.SketchManager.InsertSketch(True)
    model.EditRebuild3
    print(f"{sketch_type.capitalize()} sketch created.")
    return model


def add_dimensions(model, dimensions_text):
    """Use Claude to interpret dimension instructions and apply them."""
    prompt = (
        "You are a SolidWorks automation assistant. The user wants to add "
        "or modify dimensions on the current sketch. They said:\n\n"
        f'"{dimensions_text}"\n\n'
        "Extract the numeric dimension values (in metres) and which sketch "
        "entities they apply to. Respond with a short summary of the changes."
    )
    response = get_claude_response(prompt)
    print("Dimension guidance:", response)


# ---------------------------------------------------------------------------
# Feature operations (extrude, fillet, chamfer, pattern, mirror)
# ---------------------------------------------------------------------------
def extrude_sketch(model, depth=0.01):
    """Boss-extrude the most recent sketch by the given depth (metres)."""
    feat_mgr = model.FeatureManager
    feat_mgr.FeatureExtrusion3(
        True, False, False, 0, 0,
        depth, 0,
        False, False, False, False,
        0, 0,
        False, False, False, False,
        True, True, True,
        0, 0, False,
    )
    model.EditRebuild3
    print(f"Extruded sketch by {depth} m.")


def add_fillet(model, radius=0.005):
    """Add a fillet to the currently selected edge(s)."""
    feat_mgr = model.FeatureManager
    feat_mgr.FeatureFillet3(
        195, radius, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0,
    )
    model.EditRebuild3
    print(f"Fillet of radius {radius} m applied.")


def add_chamfer(model, distance=0.002):
    """Add an equal-distance chamfer to the currently selected edge(s)."""
    feat_mgr = model.FeatureManager
    feat_mgr.InsertFeatureChamfer(4, 1, distance, 0, 0, 0, 0, 0)
    model.EditRebuild3
    print(f"Chamfer of {distance} m applied.")


def mirror_feature(model, plane_name="Front Plane"):
    """Mirror selected feature(s) about the given plane."""
    import win32com.client
    import pythoncom
    mark = 0x00000001
    arg1 = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    model.Extension.SelectByID2(
        plane_name, "PLANE", 0, 0, 0, True, mark, arg1, 0
    )
    model.FeatureManager.InsertMirrorFeature2(
        True, False, False, False, 0
    )
    model.EditRebuild3
    print(f"Features mirrored about '{plane_name}'.")


def linear_pattern(model, direction1_count=3, direction1_spacing=0.02):
    """Create a linear pattern of the selected feature."""
    feat_mgr = model.FeatureManager
    feat_mgr.FeatureLinearPattern4(
        direction1_count, direction1_spacing,
        1, 0,
        False, False,
        "0", "0",
        False, False,
    )
    model.EditRebuild3
    print(f"Linear pattern: {direction1_count} instances, {direction1_spacing} m spacing.")


def export_model(model, path, fmt="STEP"):
    """Export the active model to STEP or STL."""
    import win32com.client
    import pythoncom
    extension = ".STEP" if fmt.upper() == "STEP" else ".STL"
    if not path.upper().endswith(extension):
        path += extension
    arg1 = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    arg2 = win32com.client.VARIANT(pythoncom.VT_BOOL, 0)
    arg3 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    arg4 = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    ret = model.Extension.SaveAs2(path, 0, 1, arg1, "", arg2, arg3, arg4)
    if ret:
        print(f"Exported to {path}")
    else:
        print("Export failed.")


# ---------------------------------------------------------------------------
# Command router using Claude (context-aware via part memory)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a SolidWorks voice-command router. Given a user's spoken command, "
    "classify it into exactly ONE of these actions and respond with ONLY the "
    "action keyword on the first line, and any numeric parameters (comma-separated) "
    "on the second line.\n\n"
    "Actions:\n"
    "  sketch     - create a new sketch (params: sketch_type, x1,y1,x2,y2 or cx,cy,r)\n"
    "  extrude    - extrude the current sketch (params: depth_in_metres)\n"
    "  fillet     - add a fillet (params: radius_in_metres)\n"
    "  chamfer    - add a chamfer (params: distance_in_metres)\n"
    "  mirror     - mirror feature (params: plane_name or empty for Front Plane)\n"
    "  pattern    - linear pattern (params: count, spacing_in_metres)\n"
    "  dimension  - add or modify dimensions on current sketch\n"
    "  export     - export model (params: file_path, format)\n"
    "  recall     - recall / show history of this part\n"
    "  quit       - exit the program\n\n"
    "If the user did not specify numeric values, use sensible defaults.\n"
    "Examples:\n"
    '  User: "draw a circle 5cm radius" -> sketch\\n0,0,0.05\n'
    '  User: "extrude 10 millimetres" -> extrude\\n0.01\n'
    '  User: "add fillet" -> fillet\\n0.005\n'
    '  User: "what have I done so far" -> recall\n'
)


def route_command(user_command, context_summary=""):
    """Use Claude to classify a voice command into an action + params."""
    system = SYSTEM_PROMPT
    if context_summary:
        system += f"\n\nPart history for context:\n{context_summary}\n"

    message = claude_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": user_command}],
    )
    raw = message.content[0].text.strip()
    lines = raw.splitlines()
    action = lines[0].strip().lower()
    params_str = lines[1].strip() if len(lines) > 1 else ""
    return action, params_str


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("SolidWorks Sketch Automation (Claude + Local Whisper STT)")
    print(f"Connected to SolidWorks {sw_version}")
    print(
        "Voice commands: sketch, extrude, fillet, chamfer, mirror, "
        "pattern, dimension, export, recall, quit\n"
    )

    active_model = None
    memory = None  # PartMemory instance, created when first sketch is made
    part_name = "Untitled"
    feature_counter = 0

    while True:
        user_command = recognize_speech()
        if not user_command:
            continue

        # Build context from memory if available
        context_summary = ""
        if memory:
            context_summary = memory.build_context_summary(user_command)

        action, params_str = route_command(user_command, context_summary)
        print(f"Action: {action}  Params: {params_str}")

        # Parse numeric params where applicable
        params = []
        if params_str:
            try:
                params = [float(v.strip()) for v in params_str.split(",")]
            except ValueError:
                params = [params_str]

        if action == "sketch":
            sketch_sub = parse_sketch_command(user_command)
            sub_lines = sketch_sub.strip().splitlines()
            sketch_type = sub_lines[0].strip().lower()
            sketch_params = []
            if len(sub_lines) > 1:
                try:
                    sketch_params = [
                        float(v.strip()) for v in sub_lines[1].split(",")
                    ]
                except ValueError:
                    sketch_params = []

            print(f"Creating a {sketch_type} sketch...")
            active_model = create_sketch(sketch_type, *sketch_params)
            feature_counter += 1

            # Initialise memory for this part
            part_name = f"Part_{feature_counter}"
            memory = PartMemory(
                part_name, qdrant_url=qdrant_url, ollama_url=ollama_url
            )

            # Generate and apply descriptive label
            label = generate_feature_label(
                f"sketch_{sketch_type}", user_command,
                sketch_params, context_summary,
            )
            rename_sw_feature(active_model, f"Sketch1", label)

            # Record in memory
            memory.record_feature(
                feature_type=f"sketch_{sketch_type}",
                label=label,
                user_intent=user_command,
                parameters={"type": sketch_type, "coords": sketch_params},
            )
            print(f"[Memory] Recorded: {label}")

        elif action == "extrude":
            if active_model and memory:
                depth = params[0] if params else 0.01
                extrude_sketch(active_model, depth)
                label = generate_feature_label(
                    "extrude", user_command, {"depth": depth}, context_summary
                )
                rename_sw_feature(active_model, "Boss-Extrude1", label)
                memory.record_feature(
                    feature_type="extrude", label=label,
                    user_intent=user_command,
                    parameters={"depth": depth},
                )
                print(f"[Memory] Recorded: {label}")
            else:
                print("No active model. Create a sketch first.")

        elif action == "fillet":
            if active_model and memory:
                radius = params[0] if params else 0.005
                add_fillet(active_model, radius)
                label = generate_feature_label(
                    "fillet", user_command, {"radius": radius}, context_summary
                )
                memory.record_feature(
                    feature_type="fillet", label=label,
                    user_intent=user_command,
                    parameters={"radius": radius},
                )
                print(f"[Memory] Recorded: {label}")
            else:
                print("No active model. Create a sketch first.")

        elif action == "chamfer":
            if active_model and memory:
                dist = params[0] if params else 0.002
                add_chamfer(active_model, dist)
                label = generate_feature_label(
                    "chamfer", user_command, {"distance": dist}, context_summary
                )
                memory.record_feature(
                    feature_type="chamfer", label=label,
                    user_intent=user_command,
                    parameters={"distance": dist},
                )
                print(f"[Memory] Recorded: {label}")
            else:
                print("No active model. Create a sketch first.")

        elif action == "mirror":
            if active_model and memory:
                plane = params_str if params_str else "Front Plane"
                mirror_feature(active_model, plane)
                label = generate_feature_label(
                    "mirror", user_command, {"plane": plane}, context_summary
                )
                memory.record_feature(
                    feature_type="mirror", label=label,
                    user_intent=user_command,
                    parameters={"plane": plane},
                )
                print(f"[Memory] Recorded: {label}")
            else:
                print("No active model. Create a sketch first.")

        elif action == "pattern":
            if active_model and memory:
                count = int(params[0]) if len(params) >= 1 else 3
                spacing = params[1] if len(params) >= 2 else 0.02
                linear_pattern(active_model, count, spacing)
                label = generate_feature_label(
                    "linear_pattern", user_command,
                    {"count": count, "spacing": spacing}, context_summary,
                )
                memory.record_feature(
                    feature_type="linear_pattern", label=label,
                    user_intent=user_command,
                    parameters={"count": count, "spacing": spacing},
                )
                print(f"[Memory] Recorded: {label}")
            else:
                print("No active model. Create a sketch first.")

        elif action == "dimension":
            if active_model and memory:
                print("Say the dimensions you want to add or modify.")
                dim_cmd = recognize_speech()
                if dim_cmd:
                    add_dimensions(active_model, dim_cmd)
                    memory.record_feature(
                        feature_type="dimension_edit",
                        label="Dimension Modification",
                        user_intent=dim_cmd,
                        parameters={"raw_command": dim_cmd},
                    )
            else:
                print("No active model. Create a sketch first.")

        elif action == "recall":
            if memory:
                history = memory.build_context_summary()
                print("\n" + history + "\n")
            else:
                print("No part memory yet. Create a sketch first.")

        elif action == "export":
            if active_model:
                path = params_str if params_str else "model.STEP"
                export_model(active_model, path)
                if memory:
                    memory.record_feature(
                        feature_type="export", label=f"Export to {path}",
                        user_intent=user_command,
                        parameters={"path": path},
                    )
            else:
                print("No active model to export.")

        elif action == "quit":
            print("Exiting.")
            break

        else:
            print(f"Unknown action '{action}'. Try again.")

        print("Ready for next command.\n")
