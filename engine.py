"""
Progressive Portrait Engine — four-tier longitudinal analysis system.

Tiers:
  T1  every conversation  — atomic metadata extraction
  T2  every 5             — behavioral pattern clustering
  T3  every 15            — portrait narrative synthesis
  T4  every 10 (≥20)      — drift detection against established portrait
"""

import json
from db import (
    get_conversation_count,
    get_last_n_t1_atoms,
    get_analyses_by_tier,
    get_portrait,
    get_portrait_version,
    save_analysis,
    save_portrait,
)

# ── System prompts ────────────────────────────────────────────────────────────

T1_PROMPT = """\
You are a conversation analyst. Given a single user message and AI response, \
extract psychological metadata. Return JSON with exactly this structure:

{
  "mood": "positive|negative|neutral|mixed",
  "energy_level": <integer 1-10>,
  "topics": ["array of topic strings"],
  "emotional_words": ["words or phrases the user used that carry emotional weight"],
  "temporal_orientation": "past|present|future|mixed",
  "social_mentions": <integer count of references to other people>,
  "question_type": "seeking_advice|exploring_ideas|emotional_processing|factual|creative",
  "notable_phrases": ["verbatim quotes that reveal character or pattern"],
  "implicit_needs": ["what the person seems to actually want beneath the surface question"]
}

Be precise. notable_phrases must be exact quotes. implicit_needs should go \
one level deeper than the stated question. Return only JSON, no commentary.\
"""

T2_PROMPT = """\
You are a longitudinal behavioral pattern analyst.

EXISTING PATTERN KNOWLEDGE (from prior batches):
{existing_patterns}

NEW CONVERSATION ATOMS (conversations {start}–{end}):
{atoms}

Identify patterns that emerge from multiple data points — not single-conversation \
observations. Note which existing patterns are reinforced, and flag contradictions carefully.

Return JSON:
{{
  "batch_range": "{start}-{end}",
  "new_patterns": ["specific behavioral observations backed by evidence"],
  "reinforced_patterns": ["existing patterns confirmed by new evidence — quote which"],
  "contradictions": ["observations that don't fit existing patterns — important"],
  "emerging_themes": ["themes growing stronger across batches"]
}}

Be specific. Bad: "This person seems anxious." Good: "Person consistently \
pre-emptively minimizes before creative endeavors ('nothing interesting to say', \
'feel weird saying that') — functions as expectation-lowering before exposure risk."\
"""

T3_PROMPT = """\
You are synthesizing a living psychological portrait from accumulated behavioral evidence.

PATTERN HISTORY ({n} conversations, {num_batches} analysis batches):
{all_patterns}

PREVIOUS PORTRAIT (update this, do not replace it wholesale):
{existing_portrait}

Write an updated portrait. Ground every observation in specific evidence from \
the patterns above. Do not speculate beyond what the data supports.

Return JSON:
{{
  "narrative": "2-3 paragraphs of coherent psychological prose. Every claim needs evidence.",
  "implicit_values": ["4-8 values observable in behavior, not stated preferences"],
  "cognitive_style": "one precise sentence",
  "persistent_tensions": ["2-4 internal contradictions that generate recurring friction"],
  "growth_trajectory": "one paragraph — what direction this person is moving and what evidence supports it"
}}

If a previous portrait exists, explicitly note what has changed vs. what has deepened.\
"""

T4_PROMPT = """\
You are detecting psychological drift — meaningful changes in a person's patterns \
relative to their established portrait.

ESTABLISHED PORTRAIT:
{portrait}

RECENT CONVERSATION ATOMS (last {n} conversations):
{recent_atoms}

Compare recent behavior to the portrait. Look for: subtle language shifts, new topics, \
weakening old patterns, escalating intensity. Minimum evidence bar: a "shift" requires \
at least 2 data points. Do not flag single-conversation anomalies as drift.

Return JSON:
{{
  "as_of_conversation_count": {conv_count},
  "consistent_with_portrait": ["observations confirming the existing model — with evidence"],
  "shifting_patterns": ["specific changes — name the pattern, cite the evidence"],
  "emerging_not_in_portrait": ["new patterns worth watching — need 2+ data points"],
  "drift_hypothesis": "one paragraph synthesizing what might be driving detected changes"
}}\
"""

# ── Engine ────────────────────────────────────────────────────────────────────

class PortraitEngine:

    def after_conversation(self, conv_id, conn, client):
        count = get_conversation_count(conn)

        # T1 always
        self._run_t1(conv_id, count, conn, client)

        # T2 every 5
        if count % 5 == 0:
            batch_start = count - 4
            self._run_t2(conv_id, batch_start, count, conn, client)

        # T3 every 15
        if count % 15 == 0:
            self._run_t3(conv_id, count, conn, client)

        # T4 every 10, only after a portrait exists
        if count % 10 == 0 and count >= 20 and get_portrait(conn):
            self._run_t4(conv_id, count, conn, client)

    # ── Tier runners ────────────────────────────────────────────────────────

    def _run_t1(self, conv_id, count, conn, client):
        from db import get_recent_conversations
        recent = get_recent_conversations(conn, 1)
        if not recent:
            return
        convo = recent[0]
        user_content = (
            f"USER: {convo['user_message']}\n\nASSISTANT: {convo['assistant_response']}"
        )
        result = self._call(client, T1_PROMPT, user_content)
        result["conversation_index"] = count
        save_analysis(conn, conv_id, "t1", result)

    def _run_t2(self, conv_id, batch_start, batch_end, conn, client):
        atoms = get_last_n_t1_atoms(conn, 5)
        existing = get_analyses_by_tier(conn, "t2")
        existing_str = json.dumps(existing, indent=2) if existing else "None yet."

        prompt = T2_PROMPT.format(
            existing_patterns=existing_str,
            start=batch_start,
            end=batch_end,
            atoms=json.dumps(atoms, indent=2),
        )
        result = self._call(client, prompt, "Analyze the pattern batch above.")
        save_analysis(conn, conv_id, "t2", result)

    def _run_t3(self, conv_id, count, conn, client):
        all_t2 = get_analyses_by_tier(conn, "t2")
        existing_portrait = get_portrait(conn)
        portrait_str = json.dumps(existing_portrait, indent=2) if existing_portrait else "None — this is the first portrait."

        prompt = T3_PROMPT.format(
            n=count,
            num_batches=len(all_t2),
            all_patterns=json.dumps(all_t2, indent=2),
            existing_portrait=portrait_str,
        )
        result = self._call(client, prompt, "Synthesize the portrait.")
        result["generated_at_conversation"] = count
        version = get_portrait_version(conn) + 1
        save_portrait(conn, result, version)
        save_analysis(conn, conv_id, "t3", result)

    def _run_t4(self, conv_id, count, conn, client):
        portrait = get_portrait(conn)
        recent_atoms = get_last_n_t1_atoms(conn, 10)

        prompt = T4_PROMPT.format(
            portrait=json.dumps(portrait, indent=2),
            n=len(recent_atoms),
            recent_atoms=json.dumps(recent_atoms, indent=2),
            conv_count=count,
        )
        result = self._call(client, prompt, "Detect drift.")
        save_analysis(conn, conv_id, "t4", result)

    # ── OpenAI call ─────────────────────────────────────────────────────────

    def _call(self, client, system_prompt, user_content):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return json.loads(response.choices[0].message.content)
