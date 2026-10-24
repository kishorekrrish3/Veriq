# VERIQ — 3-Minute Demo Script

> **Product**: VERIQ  
> **Tagline**: *Code is generated. Proof is earned.*  
> **Hackathon**: Nebius × NVIDIA Global AI Hackathon (October 2026)

---

## Video & Presentation Walkthrough

### 0:00 – 0:25: Introduce the Coding Problem
- **Visual**: Open VERIQ Developer Workbench on `http://localhost:8000`. Highlight the clean dark graphite UI (`#0B0D12`), geometric VERIQ logo, and brand statement: *"Code is generated. Proof is earned."*
- **Spoken Audio**:
  > *"Every AI coding assistant generates code, but none prove what they've built. LLMs assert that code is correct, yet real engineering requires deterministic proof. Meet VERIQ, an evidence-driven autonomous engineering agent built on Nebius Token Factory with NVIDIA Nemotron models."*
- **Action**: Click **New Run**, select the **Scientific Calculator** repository, and specify the task: *"Add Standard Deviation Calculation with Boundary Safeguards"*.

---

### 0:25 – 0:55: Model Inference & Documentation Research
- **Visual**: Hit **Launch Evidence-Driven Run**. Watch the live event timeline stream in real time.
- **Spoken Audio**:
  > *"Notice what happens first: VERIQ doesn't jump straight to guessing. It snapshots the repository into an isolated sandbox so user code is never touched. It invokes Tavily to ground the solution against official Python math documentation, and routes the task to an NVIDIA Nemotron model based on complexity."*
- **Action**: Point out the `RESEARCH_COMPLETED` event and the `MODEL_SELECTED` card displaying model telemetry (tier, latency, and estimated cost).

---

### 0:55 – 1:35: The Patch and the Failing Regression Test
- **Visual**: The diff viewer updates with the generated code patch in `calculator.py`. A few moments later, a red alert appears: `FAILURE_DETECTED`.
- **Spoken Audio**:
  > *"Here is VERIQ's core differentiator in action. The model generated the standard deviation method, but in modifying the file, it inadvertently introduced a subtle regression: factorial(-1) returned 0 instead of raising ValueError. Under AST syntax parsing, the code was valid. But in the isolated pytest check, it failed. Instead of silently claiming success, VERIQ records the failure directly into the Verification Ledger."*
- **Action**: Highlight the pytest failure output and the `FAILED` status badge in the timeline.

---

### 1:35 – 2:15: Bounded Self-Repair & Nemotron Escalation
- **Visual**: Watch the state machine transition to `REPAIRING`. The Model Router escalates from the initial tier to **NVIDIA Nemotron-340B** (`ESCALATION`).
- **Spoken Audio**:
  > *"VERIQ activates bounded self-repair. It feeds the sanitized pytest failure diagnostics into its escalation model—NVIDIA Nemotron-340B. The model diagnoses the regression and produces a minimal surgical fix without touching unrelated logic. The patch is reapplied to the sandbox, AST is rechecked, and pytest reruns: 8 passed, 0 failed."*
- **Action**: Point to the new green diff and the `REPAIR_COMPLETED` event.

---

### 2:15 – 2:45: Inspecting the Verification Ledger
- **Visual**: Scroll down to the embedded **Verification Ledger**. Click on individual claims to expand their backing evidence.
- **Spoken Audio**:
  > *"Every single claim in VERIQ is backed by inspectable proof. In this ledger, we see Claim 001 verified by SHA-256 integrity, Claim 002 verified by Python AST parsing, Claim 003 verified by isolated module imports, and Claim 004 verified by pytest exit code 0. Notice the explicit limitations listed on each claim: VERIQ honestly states what the test proves and what it does not prove."*
- **Action**: Click on **Claim-004** to expand stdout, exit code, and explicit limitations.

---

### 2:45 – 3:00: Summary of Verified Behavior & Remaining Risks
- **Visual**: Click **Download Report (.md)** to show the generated Markdown engineering report.
- **Spoken Audio**:
  > *"VERIQ never claims zero hallucination or universal perfection. It gives engineers inspectable proof, bounded repair, and transparent telemetry. Code is generated. Proof is earned. Thank you."*
- **Action**: Switch to the **Benchmarks** tab showing reproducible metrics comparing single-model baseline vs. the routed cascade.

---

## Quick Demo Launch Instructions

```bash
# Start backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Open in browser
http://localhost:8000
```
