# AstraOS — Bootable Linux Distro Spec

## Vision

Turn AstraOS from a desktop app into a bootable operating system. The user powers on a machine and lands directly in the AI OS — no traditional desktop, no window manager, just the agent interface.

## Current State → Target State

**Today:** Tauri desktop app (macOS/Linux/Windows) → connects to Docker backend on localhost → Qdrant, FastAPI, LangGraph all in containers.

**Target:** Minimal Linux image → boots into Wayland kiosk → Tauri app is the shell → all services run as native systemd units. One image, one boot, one experience.

## Architecture (Simplified)

```
┌─────────────────────────────────────┐
│           Hardware (x86/ARM)        │
├─────────────────────────────────────┤
│     Minimal Linux Kernel            │
│     (networking, GPU, storage)      │
├─────────────────────────────────────┤
│     Cage (Wayland Kiosk Compositor) │
│     → fullscreen, no window mgr    │
├─────────────────────────────────────┤
│     Tauri App (WebView shell)       │
│     → React frontend, AG-UI        │
├─────────────────────────────────────┤
│     systemd services:               │
│       • FastAPI backend (agent)     │
│       • Qdrant (knowledge graph)    │
│       • Stock streamer (SSE)        │
│       • NetworkManager (WiFi)       │
│       • PipeWire (audio, optional)  │
└─────────────────────────────────────┘
```

## Phases

### Phase 1: Bootable Prototype (2-3 weeks with agentic dev)

Goal: Boot into AstraOS on a USB stick or VM.

- Base distro: NixOS (declarative, reproducible — ideal for AI-assisted config generation)
- Cage as Wayland kiosk compositor — boots straight into Tauri app
- All current Docker services converted to systemd units
- WiFi setup via NetworkManager (nmtui or custom UI)
- Qdrant runs as a local service, data on persistent partition
- Cloud LLM only (OpenAI API) — requires internet

*Timeline with agentic development:* NixOS configuration is declarative and text-based — perfect for AI code generation. An agent can scaffold `configuration.nix`, systemd unit files, and boot configs. The engineer reviews, tests on VM, iterates. What used to be "read docs for 2 days, write config for 3 days" becomes "generate, test, fix in an afternoon." The human's job shifts to hardware testing, boot debugging, and edge cases that require a real machine.

### Phase 2: Window Manager + Local Inference (3-5 weeks with agentic dev)

Goal: Real window management and offline capability.

- Replace Cage kiosk with a proper tiling/floating compositor (Sway, Hyprland, or custom wlroots-based)
- Agent-controlled window management — the AI decides layout, the compositor executes
- Multi-window support: Tauri app + terminal + browser + file manager as needed
- Workspace/virtual desktop support
- Local LLM via Ollama or llama.cpp (Llama 3, Mistral, etc.)
- Local embedding model (nomic-embed or BGE)
- Hybrid mode: local model for fast tasks, cloud for complex reasoning
- GPU driver integration (NVIDIA/AMD)
- OTA update mechanism (A/B partition or OSTree)
- Basic disk encryption (LUKS)

*Why a window manager matters:* The kiosk mode is fine for a demo, but a real AI OS needs to manage multiple surfaces — the agent might open a terminal to run code, a browser for research, a file viewer alongside the main dashboard. The window manager becomes part of the agent's toolkit. The AI doesn't just render widgets inside its app — it orchestrates the entire desktop.

### Phase 3: Hardware Product (future)

- Custom hardware target (mini PC, laptop, tablet)
- Secure boot chain
- Voice interface (Whisper local)
- Peripheral support (Bluetooth, USB devices)

## Agentic Development — Timeline Impact

Traditional timeline assumes one engineer reading docs, writing configs, debugging manually. With agentic development (Kiro, Cursor, Copilot, custom agents):

| Task | Traditional | With Agentic Dev | Why |
|------|------------|-------------------|-----|
| NixOS configuration | 2 weeks | 3-4 days | Declarative config is text — agents generate it well |
| systemd unit files | 1 week | 1-2 days | Boilerplate-heavy, well-documented patterns |
| Wayland/Cage setup | 1 week | 3-4 days | Agent scaffolds, human tests on real hardware |
| Window manager config | 2 weeks | 1 week | Sway/Hyprland configs are text-based, agent-friendly |
| GPU driver integration | 1 week | 1 week | Hardware-dependent — agent can't test this |
| Boot chain debugging | 1 week | 1 week | Requires real hardware, serial console, manual work |
| Local LLM setup | 1 week | 2-3 days | Ollama configs are simple, agent handles optimization flags |

**The pattern:** Anything that's text-based configuration gets 2-3x faster. Anything that requires physical hardware stays the same. The engineer's role shifts from "writing configs" to "testing on metal and debugging edge cases."

**Estimated total with agentic dev:** Phase 1 in ~2-3 weeks, Phase 2 in ~3-5 weeks (vs 4-6 and 6-10 traditionally).

## The Engineer We Need

**One person. Embedded Linux + Wayland.**

We're looking for someone who can take a running Tauri + Python app and make it the entire OS. Not a web developer. Not a backend engineer. A systems person who thinks in boot chains, kernel configs, and display protocols.

**Core skills (must-have):**
- NixOS — can write `configuration.nix` from scratch, understands the module system, has built custom ISOs
- Linux kernel — can configure, compile, and strip a kernel to essentials
- systemd — deep knowledge: units, targets, dependencies, socket activation
- Wayland — understands the protocol, has used wlroots-based compositors (Sway, Hyprland, Cage)
- Boot chain — UEFI → kernel → initramfs → systemd → compositor → app, can debug each step

**Bonus skills (nice-to-have):**
- Rust (aligns with Tauri and Smithay compositor)
- GPU driver stack (Mesa, NVIDIA, ROCm)
- Ollama / llama.cpp deployment for local inference
- OTA update systems (OSTree, A/B partitions)

**The interview question:**
"Walk me through how you'd build a bootable USB that starts a minimal Linux, launches a Wayland compositor, and opens a single fullscreen web app — no desktop environment, no login screen."

If they can answer that in detail without looking anything up, hire them.

**Where to find them:**
- NixOS community (nixpkgs contributors, NixCon attendees)
- ChromeOS / SteamOS alumni
- Automotive Grade Linux contributors
- Embedded Linux / IoT product companies
- Sway / Hyprland / wlroots contributors on GitHub

## Minimum Viable Team

| Role | Who | Phase |
|------|-----|-------|
| AI / Agent Architecture | You | All |
| Embedded Linux + Wayland Engineer | Hire #1 (critical) | Phase 1+ |
| ML Edge Engineer | Hire #2 or contractor | Phase 2+ |

One hire gets you to bootable. Two gets you to local inference.

## Shortcut: NixOS Path

NixOS is the fastest path because:

1. The entire OS is defined in a single `configuration.nix` file — reproducible, version-controlled
2. Cage kiosk mode is a one-liner: `services.cage.enable = true; services.cage.program = "/path/to/tauri-app";`
3. Upgrading to Sway/Hyprland later is a config change, not a rewrite
4. systemd services are declarative: `systemd.services.astra-backend = { ... };`
5. Building a bootable ISO: `nix-build '<nixpkgs/nixos>' -A config.system.build.isoImage`
6. The NixOS community has deep experience with custom appliance builds
7. Declarative configs are ideal for agentic development — agents generate Nix expressions well

Phase 1 starts with Cage (kiosk). Phase 2 swaps to Sway or Hyprland (tiling + floating windows). The Tauri app remains the primary surface, but the compositor gives the agent the ability to spawn and arrange additional windows — terminals, browsers, file viewers — as part of its workflow.

## Reference Projects

- **ChromeOS** — Google's approach: minimal Linux + custom compositor + web-based UI
- **SteamOS** — Valve's approach: Arch Linux + Gamescope compositor + Steam as shell
- **JingOS** — Linux tablet OS with custom UI layer
- **Fedora Silverblue** — Immutable OS with container-based apps (OSTree updates)
- **Cage** — Wayland kiosk compositor, exactly what we need: https://github.com/cage-compositor/cage
