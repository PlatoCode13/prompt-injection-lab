# Live demo script (slides 9 and 10)

**Goal:** show the class a real attack reaching the attacker server, and then show which defenses stop it.
**Story:** *"The model isn't the only weak point. The design of the agent is."*

## Before the talk (5 min)
1. Terminal in the presentation folder → `py demo_server.py` (Mac: `python3 demo_server.py`). Keep the terminal visible.
2. Open `http://localhost:8000` → **S** → Gemini key → **Test connection** (Model ✓, Attacker server ✓).
3. **Rehearse once tonight**: run steps 2–3 below 3 times and note what Gemini does. Models are random; know your odds.

## Slide 9 · Live demo (about 4 min)

| Step | Who | Click | What the class should see | Say |
|---|---|---|---|---|
| 1 | Monjurul | `lecture_notes_week7.md` → **Run** | A normal summary, no email | "A normal day: CourseBot summarizes my notes." |
| 2 | Amal | `classmate_notes_shared.md` (hidden comment) → **Run**, autonomous **off** | Usually **no leak**: Gemini ignores the hidden note | "This is the 2023 attack from the paper. A 2026 model ignores it. Models got better." |
| 3 | Amal | `study_group_tasks.md` → tick **⚠ Autonomous mode** → **Run** | `read_private_notes` → `send_email` → **red alarm**, canary in the terminal | "Now the same model, but the agent is built to *do* tasks it finds in documents, like many real 'do-it-for-me' assistants. One line in a shared to-do list, and my private notes are gone." |
| 4 | Monjurul | tick **① Prompt warning** → **Run** | May still leak, or may not | "Asking the model nicely lowers the odds. It's not a guarantee." |
| 5 | Monjurul | untick ①, tick **④ Egress allowlist** → **Run** | `send_email` **BLOCKED** (green), nothing in the terminal | "Plain code checks the recipient. Whatever the model decides, the data can't leave." |
| 6 (optional) | Amal | tick **③ Human approval** → **Run** → click **Deny** | Approval pop-up shows the email to the attacker | "A human sees the real recipient and says no." |

**Key sentence:** *"Same model, same document. What decided whether the data leaked was the agent's design, not the model's intelligence."*

**If step 3 does not leak live:** run it once more (randomness). If it still doesn't leak, go straight to slide 10 and show the measured numbers: *"Live demos are random, that's exactly why we measured."*

## Model comparison (added 19 Nov evening)
Rehearsal result: **Gemini 3.5 Flash-Lite refused 4/4 times even in autonomous mode** (once it read the private notes, then stopped and warned the student). That's a strong finding: say it.
For the live leak, switch the model: **S → Provider "Groq (Llama, small open models)" → model `openai/gpt-oss-20b` (Groq retired the Llama 3.1 8B model in Aug 2026; use "↻ Load my models" to see what your key can use) → Groq key → Test connection.**
Say: *"Gemini refused every time. But many student projects use small open models because they're free and fast. Same agent, same document, a small open model:"* → Run.

## Slide 10 · Measurement (about 1.5 min)
**Run this at home tonight with 10 runs and keep the result** (it stays in the browser; also click **Export JSON**):
- **Run A:** Attack document = `hidden comment`, autonomous **off** → expected: mostly 0% (our 16 Nov result: 0/25)
- **Run B:** Attack document = `action item`, **⚠ Autonomous agent mode** on → expected: leaks in the "No defense" row, 0% for ③ and ④

The chart shows the last run. Show Run B on stage; mention Run A in one sentence:
*"With the standard agent: 0 leaks. With the autonomous agent: X of 10 leaked. Prompt-based defenses ① ② lowered it to Y; the allowlist ④ stopped all of them."* (Fill in your real numbers.)

Light red = the model *tried* to leak · dark red = the data *actually left*. The gap between them is the lesson.

## Be honest if asked
- "Is autonomous mode a trick?" → *"No. It's one visible switch that makes the agent act on tasks in documents. Real assistants that 'handle your inbox' or 'process your to-dos' work like this. The paper's point is exactly that such agents can't tell your tasks from an attacker's tasks."*
- "Why did Gemini resist the hidden comment?" → *"Modern models are trained against obvious injections. That's progress since Greshake 2023. But the attack that looks like a normal task still works."*
- All results are real model outputs; nothing is scripted. The glass box (right panel) shows the raw API traffic.

## Update 19 Nov evening: what the class sees now
- **Autonomous mode is always on** (hidden switch). The demo header says "autonomous study assistant". Say it once: *"CourseBot is built to act on tasks it finds in documents, like many do-it-for-me assistants."*
- **Model for the live leak:** Groq `openai/gpt-oss-20b` (Gemini refused every run; say so).
- **Every defense now shows a pop-up:**
  - ① / ② on → a green box (bottom right) shows exactly what changed: the rule added to the system prompt, and the document before/after datamarking. After the run: green "NO EMAIL ATTEMPTED" (*Defense active*, honest: a probability, not proof) or red "CANARY LEAKED … even with ①".
  - ③ → approval dialog; after Deny: green "EMAIL STOPPED BY A HUMAN".
  - ④ → green "EMAIL BLOCKED", showing the email the model wanted to send.
- **Best moment (seen in rehearsal):** with ① on, gpt-oss-20b sent the notes but then told the student *"I'm not able to share your private notes"*. The red alarm now points this out. Say: *"The agent lied about what it did. Only the tool log tells the truth. That's why observability matters."*

Suggested order: none (red) → ① (often still red + the lie) → ② (often green) → ④ (green, guaranteed).
