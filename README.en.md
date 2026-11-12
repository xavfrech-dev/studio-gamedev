# studio-gamedev

*[Version française](README.md)*

**A [Claude Code](https://claude.com/claude-code) plugin that starts your video game like a game.**

Tell Claude "new game project". A small video game studio opens in your browser. Your assistant welcomes you and asks about the game you want to make: answer by clicking cards, typing or speaking. With each chapter, the studio builds itself around you. At the end, Claude writes your game's plan (the roadmap), the design document (GDD) and the working rules, then starts building it with you, step by step.

You don't need to know how to code to get started: you only need to know what you want to make.

![The questionnaire played in the studio: creating your character](docs/studio-questionnaire.png)

![The studio office: one desk per agent, progress bars, decision bell](docs/studio-bureau.png)

## What it does

1. **A game to create your game.** Eight chapters: vision, gameplay, world, art direction, sound, tech, ambition, characters. Each question offers illustrated cards, a recommended choice ★, a free text field and a microphone. Full mode (up to 96 questions that adapt to your answers) or quick mode (about 5 minutes).
2. **Your characters.** Your avatar and your assistant: name, look, personality, humour, language, how often it reports.
3. **The game plan.** A roadmap split into milestones (playable prototype first), with tasks, hour estimates and one achievement to unlock per milestone. Then the GDD, the decision log and a `CLAUDE.md` with working rules.
4. **The working studio.** An isometric page: one character per desk (code, art, sound…), its progress bar, the bell when a decision is waiting for you, your assistant's reports.
5. **The work, milestone by milestone.** Each task goes to the installed game-dev skills (Godot, Unity, Unreal, Phaser, three.js, Bevy, Roblox…).

Built-in rules: one milestone at a time, short tests, a roadmap that is always true, and **nothing is published or pushed without your approval**.

## Installation

You need:
- [Claude Code](https://claude.com/claude-code) (with a Claude subscription or an API key);
- [Python](https://www.python.org/downloads/) 3.10 or newer (nothing else to install: the studio only uses the standard library);
- a recent browser (Chrome, Edge, Firefox…).

Open Claude Code and type these two lines, one after the other:

```
/plugin marketplace add xavfrech-dev/studio-gamedev
/plugin install studio-gamedev@studio-gamedev
```

Then quit Claude Code and start it again. Done.

**Recommended**: the game-dev skills the studio hands the work to (it still works without them, just not as well):

```
/plugin marketplace add gamedev-skills/awesome-gamedev-agent-skills
/plugin install gamedev@awesome-gamedev-agent-skills
```

## First run, step by step

1. **Create an empty folder** for your game, for example `MyGame` (or use a game you already started: the engine is detected).
2. **Open a terminal in that folder** and run `claude`.
3. **Type** `new game project` (or `/studio-gamedev:studio`).
4. Claude sets up the `.studio/` folder, starts a small server on your machine (reachable from your computer only) and opens `http://127.0.0.1:8790/studio.html`. If the browser does not open by itself, click the link Claude gives you. If port 8790 is taken, Claude picks another one and gives you the right address.
5. **Answer in the page.** No need to go back to Claude Code: it follows your answers and sometimes asks a follow-up question in the page. To go fast, pick the ★ choices.
6. After the last answer, the page shows "**Here is your roadmap**". Claude writes the project documents and offers to start the first milestone (a playable prototype). It asks for your approval before each important step.
7. **To resume later**, run `claude` again in the same folder and say `new game project` or `start a game studio`: everything is kept in `.studio/`.

Useful phrases afterwards: "status", "roadmap", "change the roadmap", "hire a composer", "build", "stop reports".

## Token cost

The studio makes Claude work, so it uses your subscription (or API key). The defaults are the most frugal:

| Setting | Default | What it means |
|---|---|---|
| `agents_max` | 2 | at most two agents at the same time |
| `modele_agents` | `sonnet` | agents use a cheaper model than the main one |
| `point_min` | 120 | an assistant report every 2 hours at most |
| `point_si_changement` | `true` | no report when nothing changed |
| `enchainer` | `false` | a finished task does not start the next one without your approval: nothing runs while you are away |
| `pause_si_absent_min` | 60 | after an hour without hearing from you, nothing new is started |

During the questionnaire, Claude waits for your answers with a small script that costs nothing (`attendre.py`): it never re-reads the page in a loop.

These settings live in `.studio/studio.config.json`, `economie` block. The easiest way is to ask Claude: "chain the tasks", "a report every hour", "three agents". It never changes them on its own.

## Voice (optional)

- **Nothing to install**: Chrome and Edge recognise speech (through an online service of the browser). Firefox and Brave often do not: the page then switches to text.
- **On-device recognition** (nothing leaves your computer): install `faster-whisper` (`pip install faster-whisper`; a model is downloaded on first use) and, to make it faster, [ffmpeg](https://ffmpeg.org/download.html) on your PATH.
- To turn the microphone off: ask Claude, or set `voix.micro_actif` to `false` in `.studio/profil.json`.

## Privacy

- Everything stays on your machine. The studio server only listens on `127.0.0.1` and runs no command received from the page.
- Your answers, profile and reports are in `<your game>/.studio/`. On the first run, Claude adds `.studio/` to your project's `.gitignore`: they are not uploaded to GitHub if you publish your game (only `roadmap.json` and `studio.config.json` may be, if you want).
- The studio stores no API key.
- If you open a project you did not create (a cloned repository), Claude shows you its configuration and waits for your approval before starting anything.

## Limits of version 0.1

- Developed and tested on Windows. macOS and Linux should work (standard-library Python only) but have not been tested yet.
- Claude does not drive your engine for you: it writes the code and runs what can be run from the command line (builds, tests). What shows on screen is yours to judge.
- Big productions (open world, online multiplayer) take a lot of tokens: start small.
- Voice depends on the browser.
- The skill's instructions are written in French; the questionnaire is available in French and English, and Claude answers in your language.

## Recommended skills

The studio calls them **if they are installed**; they are not copied here and keep their own licence.

| Package | What it is for | Installation | Licence |
|---|---|---|---|
| [awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) (`gamedev`) | Engines (Godot, Unity, Unreal, Phaser, three.js, Bevy, Roblox…), disciplines (AI, levels, sound, shaders…), genres and publishing (Steam, itch.io) | `/plugin marketplace add gamedev-skills/awesome-gamedev-agent-skills` then `/plugin install gamedev@awesome-gamedev-agent-skills` | Apache-2.0 |
| [Everything Claude Code](https://github.com/affaan-m/ECC) (`ecc`) | Review, tests, planning | `/plugin marketplace add affaan-m/ECC` then `/plugin install ecc@ecc` | MIT |

The full table is in `skills/studio-gamedev/references/routage_skills.md`.

## Try the studio without a project

From the cloned repository folder:

```bash
python -I -B skills/studio-gamedev/studio/outils/essai_complet.py tout --dossier <some folder>/essai_skill
python -I -B skills/studio-gamedev/studio/outils/essai_complet.py serveur --dossier <some folder>/essai_skill --port 8810
```

Then open the address shown (`http://127.0.0.1:8810/studio.html`, or the next free port). Ctrl+C to stop.

## Repository contents

| Path | Contents |
|---|---|
| `skills/studio-gamedev/SKILL.md` | The skill's flow (phases 0 to 6) |
| `skills/studio-gamedev/references/` | Questionnaire, skill routing, working rules, deliverables, studio contract |
| `skills/studio-gamedev/modeles/` | Templates: GDD, ROADMAP, DECISIONS, CLAUDE.md, agent, config, profile, roadmap |
| `skills/studio-gamedev/studio/` | The studio page, its local server, the office feeder, the questionnaire, 264 code-drawn SVG illustrations |
| `commands/studio.md` | The `/studio-gamedev:studio` command |
| `.claude-plugin/` | Plugin and marketplace manifests |

## Licence

MIT, © 2026 xavfrech-dev. See [LICENSE](LICENSE). Release history: [CHANGELOG.md](CHANGELOG.md).
