"""
Seeds 25 mock conversations + pre-computed analysis outputs directly into the DB.
No model calls are made. Run once: python seed.py
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from db import get_conn, init_db, DB_FILE

# ── Mock conversations ────────────────────────────────────────────────────────

CONVERSATIONS = [
    {
        "user": "How do I stop second-guessing my decisions at work after I've already made them?",
        "assistant": "Second-guessing tends to increase the less concrete your decision criteria were upfront. One technique: before deciding, briefly write down what 'good enough' looks like and what would justify reversing the decision later. After committing, treat new information as 'updating the model going forward' rather than 'evidence I was wrong.' The goal isn't inflexibility — it's separating the quality of the decision from the quality of the outcome, which you can't fully control anyway.",
    },
    {
        "user": "Explain distributed caching like I've never heard of it.",
        "assistant": "Distributed caching stores frequently accessed data in fast in-memory stores spread across multiple nodes, closer to your application than the database. The core tradeoff is read speed vs. consistency — cached data can go stale. Cache invalidation is the hard problem: decide upfront whether your use case needs strong consistency (cache-aside, read-through) or can tolerate eventual consistency (write-behind). For most web workloads, a TTL-based cache-aside pattern covers 80% of cases.",
    },
    {
        "user": "I've been thinking about whether therapy is worth it for someone who is basically fine.",
        "assistant": "The 'basically fine' frame is worth examining. Therapy isn't only for people in crisis — it's useful for anyone who wants to understand their own patterns or has a recurring problem they haven't solved alone. The ROI depends heavily on therapist fit, which takes a few tries to find. Many people do a few sessions, find it unhelpful, and conclude therapy doesn't work — when they may have just had the wrong therapist. A single consultation with 2-3 different therapists before committing is a reasonable approach.",
    },
    {
        "user": "What's the best way to structure a difficult conversation with a coworker?",
        "assistant": "Structure it as: observation → impact → request. 'I noticed X. Here's how that affected Y. I'd like Z going forward.' Lead with curiosity before conclusions — 'I noticed X, and I'm wondering if there's something I'm missing.' The most common failure mode is waiting until you're already frustrated, which makes the emotional charge visible and puts the other person on defense before you've said anything.",
    },
    {
        "user": "I keep starting personal projects and abandoning them halfway. What's actually going on?",
        "assistant": "Starting-and-abandoning is usually a mismatch between the reward you're expecting and the actual reward cycle of the project. Early stages feel generative and novel; middle stages feel like work with no visible progress. One fix: define a 'minimum complete' version before starting — small enough to finish in a week. Finishing something small trains the follow-through habit. The goal isn't the project; it's the muscle of completion.",
    },
    {
        "user": "Why does running improve my mood so reliably?",
        "assistant": "Running triggers a reliable stress-hormone flush — cortisol and adrenaline drop post-exercise. It also increases BDNF, which supports mood regulation and neuroplasticity. But there may be a simpler mechanism too: running has an unambiguous end point. Unlike most cognitive work, a run is clearly finished. That sense of earned, measurable completion may be as mood-relevant as the biochemistry.",
    },
    {
        "user": "I want to write more but I always feel like I have nothing interesting to say.",
        "assistant": "The 'nothing interesting to say' feeling is almost always a filtering problem, not an originality problem. You're rejecting ideas before articulating them, based on an imagined audience reaction that isn't real yet. Two exercises: write a shitty first draft for 10 minutes with no editing; or explain something you recently learned to someone who knows nothing about it. The ideas are there — the internal editor is just running too early.",
    },
    {
        "user": "My coworker takes partial credit for team work in readouts. How do I address it without it becoming a whole thing?",
        "assistant": "Document your contributions explicitly and visibly before and after group work — in meeting notes, in Slack, in follow-up emails. This isn't being defensive; it's building a paper trail that speaks for itself. If the behavior continues, a direct one-on-one: 'I noticed my contributions weren't mentioned in the readout for X. I'd like to figure out how we share credit more visibly going forward.' Keep it forward-looking, not accusatory.",
    },
    {
        "user": "Walk me through event sourcing and when you'd actually use it in production.",
        "assistant": "Event sourcing stores state as a sequence of immutable events rather than the current value. Current state is derived by replaying the event log. CQRS separates the write model from the read model, often using event sourcing on the write side. The real-world use case: when you need audit trails, time-travel debugging, or multiple read projections from the same data. The tradeoffs are significant — eventual consistency, more storage, harder debugging. Reach for it when audit or temporal requirements make the complexity worth it, not as a default.",
    },
    {
        "user": "I've been feeling more disconnected from friends than usual lately. Is that normal?",
        "assistant": "Yes, and it's usually a combination of reduced shared context (you're less in each other's daily lives) and asymmetric effort — one person ends up initiating more. Adult friendships require deliberate maintenance in a way they didn't when proximity was automatic. One practical shift: instead of open-ended 'we should catch up,' propose something specific with a time and place. Specificity dramatically increases follow-through.",
    },
    {
        "user": "What separates people who are really good at giving feedback from people who aren't?",
        "assistant": "Good feedback-givers do a few things consistently: they lead with curiosity rather than conclusions, they describe observable behavior rather than character, and they time it well — not in the heat of the moment, not so delayed it's forgotten. The rarest skill is separating 'what I observed' from 'what I made that mean' — the gap between those two is where most feedback goes wrong. The interpretation is usually the problem, not the observation.",
    },
    {
        "user": "I made shakshuka for the first time and it turned out great. Why does cooking feel so satisfying?",
        "assistant": "Cooking hits several psychological needs simultaneously: it has a clear start and end (completion reward), produces a tangible artifact rare in knowledge work, provides immediate sensory feedback, and constrains creativity productively. You're working within ingredients and time, which tends to generate more satisfaction than total open-endedness. It's why many engineers are decent cooks — both are about making something real within constraints, and the feedback loop is immediate.",
    },
    {
        "user": "I'm genuinely good at my job but I feel weird saying that out loud. Why?",
        "assistant": "Claiming competence aloud carries social risk that privately knowing it doesn't. You might seem arrogant, or you might be wrong in front of someone. There's also a ratchet effect: once you've claimed capability, you're held to it. What's worth noticing: privately knowing you're good is epistemically identical to saying it. The discomfort isn't about the truth of the statement — it's about the perceived cost of making it public. That's worth examining.",
    },
    {
        "user": "How do I stop comparing myself to engineers who seem more accomplished at my age?",
        "assistant": "Comparison tends to be asymmetric. You're comparing your interior experience — doubts, struggles, imposter moments — to other people's exterior presentation: what they ship, how they talk in meetings, their visible confidence. You're rarely comparing like with like. One useful reframe: identify specifically what they do that you'd want to be able to do, and whether it's actually learnable. That converts envy into a concrete target.",
    },
    {
        "user": "What's the psychological difference between loneliness and solitude?",
        "assistant": "The functional difference is agency and felt connection. Solitude is chosen aloneness that feels restful; loneliness is aloneness — chosen or not — accompanied by a sense of disconnection. You can be lonely in a crowd and not lonely while alone. The key variable isn't physical isolation — it's whether you feel your inner world is known and held by others, even if they're not present.",
    },
    {
        "user": "I want to get better at saying no without feeling guilty afterward.",
        "assistant": "Guilt after saying no often means you've declined the request but not the identity of being the person who always says yes. One reframe: saying no is resource allocation, not rejection. It's also worth examining whether the guilt is about the other person's actual disappointment, or about a threat to your self-image as someone helpful. Often it's the latter — and you can interrogate that image more directly.",
    },
    {
        "user": "Why do I feel guilty when I'm not being productive, even on weekends?",
        "assistant": "Productivity guilt in adults usually has one of two sources: externally-conditioned validation (you learned early that output equals worth), or anxiety management (doing something means not sitting with things that are harder to face). The test: does the guilt decrease when you're resting for a clear, sanctioned reason versus resting without justification? If yes, you probably have conditional permission to rest rather than a baseline anxiety about productivity. That conditional permission can be examined directly.",
    },
    {
        "user": "I've been having the same unresolved argument with someone for months. It never goes anywhere.",
        "assistant": "Recurring arguments that never resolve are usually about something other than their stated content. The same fight about dishes is rarely about dishes. One diagnostic: ask what each person would actually feel if they 'won.' If the underlying need isn't met by the stated resolution, winning won't end it. The real conversation is usually one layer underneath the surface disagreement — find that layer, and the surface argument often dissolves.",
    },
    {
        "user": "How does sleep actually consolidate memory? Is something real happening or is it mostly just rest?",
        "assistant": "Something real is happening. During slow-wave sleep and REM, the hippocampus replays recently acquired information and transfers it to the neocortex for long-term storage. It's an active process, not passive. Sleep deprivation impairs both encoding (before sleep) and consolidation (during). Practical implication: reviewing material before sleep and getting a full cycle meaningfully improves retention compared to reviewing and staying up.",
    },
    {
        "user": "I'm thinking about switching teams at work. How do I think through a decision like that carefully?",
        "assistant": "Map it across three dimensions: growth (will you learn things your current team can't offer?), relationships (moving toward something vs. primarily away from friction?), and optionality (does this open or close doors?). The most common mistake in team switches is optimizing too hard on the current problem without enough weight on what problems you're moving toward. Talk to 2-3 people on the target team before deciding — their answers will tell you a lot.",
    },
    {
        "user": "I got feedback that I'm 'hard to read' at work. What does that actually mean and should I care?",
        "assistant": "Being hard to read usually means your emotional state isn't visibly mapping to what's happening in the room. It's not necessarily a flaw — it often signals strong self-regulation. Whether to care depends on context: in leadership roles, legibility helps people trust you; in peer work, less so. If you want to be more readable without becoming performative, try narrating your thinking in real-time — 'I'm still processing this' or 'I'm less certain than I look.' It bridges the gap without forcing expression.",
    },
    {
        "user": "Why do I only feel really proud of myself when someone else validates it first?",
        "assistant": "External validation becomes the primary meter when internal validation hasn't been calibrated independently. In development, we learn to use external signals as proxies for quality — approval, test results, user engagement — because internal certainty is unreliable early on. The habit can persist past the point where it's necessary. The interesting question isn't why you need validation, but what internal signal you would trust if validation weren't available. That gap is worth sitting with.",
    },
    {
        "user": "I want to start informally mentoring a junior colleague but I don't feel qualified enough yet.",
        "assistant": "The 'not qualified' feeling is often a confusion between mastery and useful distance. You don't need to be an expert — you need to be far enough ahead to see terrain the other person can't see yet because they're too close to it. The most useful thing a mentor does isn't teach; it's notice. You can do that from two years ahead, not just ten. The qualification threshold you're imagining is probably higher than the one that would actually help them.",
    },
    {
        "user": "My running pace has plateaued at the same level for weeks. What's happening physiologically?",
        "assistant": "A pace plateau means your training stimulus has become routine — your aerobic system has adapted to the current load. Standard interventions: introduce variable intensity (tempo runs, intervals), increase weekly volume gradually using the 10% rule, or add a structured rest week to let adaptations consolidate. Pure easy-effort running builds an aerobic base but stops improving pace once adaptation is complete. Strides — short controlled accelerations at the end of easy runs — are a low-cost way to add neuromuscular stimulus without significant recovery cost.",
    },
    {
        "user": "I had a genuinely good week and I keep waiting for something to go wrong. Why can't I just let it be good?",
        "assistant": "This is anticipatory anxiety wearing pragmatism as a disguise. The good week feels unstable because it doesn't match your internal baseline — somewhere, you've learned that good periods precede disruption, so the good period itself becomes an anxiety signal. Worth noticing: the hypothesis 'good things don't last' is unfalsifiable in this frame, because when things do stay good, the anticipatory anxiety just extends. You're not being realistic — you're managing the threat of eventual disappointment by starting to grieve before anything's happened.",
    },
]

# ── Mock T1 atoms (per-conversation metadata) ────────────────────────────────

T1_ATOMS = [
    {"mood": "mixed", "energy_level": 5, "topics": ["self-doubt", "decision-making", "work"], "emotional_words": ["second-guessing", "wrong"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "seeking_advice", "notable_phrases": ["stop second-guessing my decisions"], "implicit_needs": ["permission to trust own judgment", "framework for decisiveness"], "conversation_index": 1},
    {"mood": "neutral", "energy_level": 6, "topics": ["distributed systems", "caching", "technical"], "emotional_words": [], "temporal_orientation": "present", "social_mentions": 0, "question_type": "factual", "notable_phrases": [], "implicit_needs": ["practical decision framework, not just definitions"], "conversation_index": 2},
    {"mood": "mixed", "energy_level": 5, "topics": ["mental health", "therapy", "self-reflection"], "emotional_words": ["basically fine"], "temporal_orientation": "future", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": ["basically fine"], "implicit_needs": ["permission to explore without admitting need", "ROI framing to rationalize curiosity"]},
    {"mood": "neutral", "energy_level": 5, "topics": ["work relationships", "conflict", "communication"], "emotional_words": [], "temporal_orientation": "future", "social_mentions": 1, "question_type": "seeking_advice", "notable_phrases": ["without it becoming a whole thing"], "implicit_needs": ["resolution without confrontation", "tactical script"], "conversation_index": 4},
    {"mood": "mixed", "energy_level": 4, "topics": ["self-discipline", "projects", "habits"], "emotional_words": ["abandoning"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "seeking_advice", "notable_phrases": ["keep starting and abandoning them halfway"], "implicit_needs": ["understanding of own follow-through patterns", "absolution for past abandonment"], "conversation_index": 5},
    {"mood": "positive", "energy_level": 7, "topics": ["running", "mood", "psychology"], "emotional_words": ["reliably"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": ["so reliably"], "implicit_needs": ["validation that the coping mechanism is real and earned"], "conversation_index": 6},
    {"mood": "mixed", "energy_level": 5, "topics": ["writing", "creativity", "self-expression"], "emotional_words": ["nothing interesting to say"], "temporal_orientation": "future", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": ["nothing interesting to say"], "implicit_needs": ["permission to start despite self-doubt", "evidence the filter is the problem not the ideas"], "conversation_index": 7},
    {"mood": "negative", "energy_level": 4, "topics": ["work", "credit", "fairness"], "emotional_words": ["takes partial credit"], "temporal_orientation": "present", "social_mentions": 1, "question_type": "seeking_advice", "notable_phrases": ["without it becoming a whole thing"], "implicit_needs": ["visibility without confrontation", "to be seen without having to demand it"], "conversation_index": 8},
    {"mood": "neutral", "energy_level": 6, "topics": ["event sourcing", "CQRS", "architecture"], "emotional_words": [], "temporal_orientation": "present", "social_mentions": 0, "question_type": "factual", "notable_phrases": [], "implicit_needs": ["practical production guidance, not textbook theory"], "conversation_index": 9},
    {"mood": "negative", "energy_level": 4, "topics": ["friendship", "loneliness", "connection"], "emotional_words": ["disconnected", "more than usual"], "temporal_orientation": "present", "social_mentions": 3, "question_type": "emotional_processing", "notable_phrases": ["more disconnected than usual lately"], "implicit_needs": ["normalization of the feeling", "agency in reversing it"], "conversation_index": 10},
    {"mood": "neutral", "energy_level": 6, "topics": ["feedback", "communication", "skill"], "emotional_words": [], "temporal_orientation": "present", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": [], "implicit_needs": ["implicit: to become better at giving feedback themselves"], "conversation_index": 11},
    {"mood": "positive", "energy_level": 7, "topics": ["cooking", "satisfaction", "psychology"], "emotional_words": ["satisfying"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": ["turned out great", "so satisfying"], "implicit_needs": ["to understand why non-work accomplishments feel as real as work ones"], "conversation_index": 12},
    {"mood": "mixed", "energy_level": 5, "topics": ["self-worth", "competence", "identity"], "emotional_words": ["feel weird", "good at my job"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "emotional_processing", "notable_phrases": ["feel weird saying that out loud"], "implicit_needs": ["permission to own competence fully", "understand the social cost logic"], "conversation_index": 13},
    {"mood": "negative", "energy_level": 4, "topics": ["comparison", "career", "self-worth"], "emotional_words": ["more accomplished", "stop comparing"], "temporal_orientation": "present", "social_mentions": 2, "question_type": "emotional_processing", "notable_phrases": ["stop comparing myself to engineers who seem more accomplished at my age"], "implicit_needs": ["stable internal metric independent of peers", "to stop using others as the benchmark"], "conversation_index": 14},
    {"mood": "neutral", "energy_level": 6, "topics": ["loneliness", "solitude", "psychology"], "emotional_words": [], "temporal_orientation": "present", "social_mentions": 0, "question_type": "exploring_ideas", "notable_phrases": [], "implicit_needs": ["to distinguish chosen aloneness from felt disconnection — probably for self-diagnostic purposes"], "conversation_index": 15},
    {"mood": "mixed", "energy_level": 5, "topics": ["boundaries", "guilt", "self-permission"], "emotional_words": ["guilty"], "temporal_orientation": "future", "social_mentions": 0, "question_type": "seeking_advice", "notable_phrases": ["without feeling guilty afterward"], "implicit_needs": ["permission to disappoint others", "reframe around guilt source"], "conversation_index": 16},
    {"mood": "negative", "energy_level": 4, "topics": ["productivity", "guilt", "rest", "self-worth"], "emotional_words": ["guilty", "not being productive"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "emotional_processing", "notable_phrases": ["feel guilty when I'm not being productive, even on weekends"], "implicit_needs": ["to understand the guilt well enough to interrupt it", "unconditional permission to rest"], "conversation_index": 17},
    {"mood": "negative", "energy_level": 4, "topics": ["conflict", "relationships", "recurring argument"], "emotional_words": ["same argument", "never goes anywhere"], "temporal_orientation": "present", "social_mentions": 1, "question_type": "seeking_advice", "notable_phrases": ["same unresolved argument for months"], "implicit_needs": ["real resolution not just ceasefire", "understanding of what the argument is actually about"], "conversation_index": 18},
    {"mood": "neutral", "energy_level": 6, "topics": ["sleep", "memory", "neuroscience"], "emotional_words": [], "temporal_orientation": "present", "social_mentions": 0, "question_type": "factual", "notable_phrases": [], "implicit_needs": ["practical application of the mechanism"], "conversation_index": 19},
    {"mood": "mixed", "energy_level": 5, "topics": ["career", "team switch", "decision-making"], "emotional_words": ["thinking about"], "temporal_orientation": "future", "social_mentions": 0, "question_type": "seeking_advice", "notable_phrases": [], "implicit_needs": ["structured framework to avoid decision paralysis", "external permission to leave current situation"], "conversation_index": 20},
    {"mood": "mixed", "energy_level": 5, "topics": ["identity", "work perception", "legibility"], "emotional_words": ["hard to read"], "temporal_orientation": "present", "social_mentions": 1, "question_type": "emotional_processing", "notable_phrases": ["hard to read"], "implicit_needs": ["understand whether controlled illegibility is a flaw or a feature", "evaluate whether to change"], "conversation_index": 21},
    {"mood": "negative", "energy_level": 4, "topics": ["validation", "self-worth", "pride", "external approval"], "emotional_words": ["only feel really proud", "validates it first"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "emotional_processing", "notable_phrases": ["only feel really proud of myself when someone else validates it first"], "implicit_needs": ["access to internal validation that doesn't require external input", "to understand the origin of the pattern"], "conversation_index": 22},
    {"mood": "mixed", "energy_level": 5, "topics": ["mentoring", "qualification", "competence"], "emotional_words": ["don't feel qualified enough yet"], "temporal_orientation": "future", "social_mentions": 1, "question_type": "seeking_advice", "notable_phrases": ["don't feel qualified enough yet"], "implicit_needs": ["permission to help before feeling like an expert", "threshold recalibration"], "conversation_index": 23},
    {"mood": "neutral", "energy_level": 6, "topics": ["running", "physiology", "training plateau"], "emotional_words": ["plateaued"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "factual", "notable_phrases": ["plateaued at the same level for weeks"], "implicit_needs": ["specific actionable intervention, not general advice"], "conversation_index": 24},
    {"mood": "positive", "energy_level": 7, "topics": ["anxiety", "good week", "anticipatory fear", "trust"], "emotional_words": ["keep waiting for something to go wrong"], "temporal_orientation": "present", "social_mentions": 0, "question_type": "emotional_processing", "notable_phrases": ["keep waiting for something to go wrong", "can't just let it be good"], "implicit_needs": ["permission to trust positive states", "understanding of anticipatory anxiety as anxiety, not realism"], "conversation_index": 25},
]

# ── Mock T2 patterns (every 5 conversations) ─────────────────────────────────

T2_BATCHES = [
    {
        "batch_range": "1-5",
        "new_patterns": [
            "Frames self-improvement goals in behavioral/tactical terms ('how do I stop X') rather than exploring the underlying emotion — this is a coping style, not ignorance of the emotion",
            "Technical questions consistently seek practical decision frameworks over theoretical understanding — curiosity is applied, not abstract",
            "Ambivalence around need: 'basically fine' (conv 3) acknowledges curiosity while minimizing the desire — a pre-emptive lowering of stakes before exposure",
        ],
        "reinforced_patterns": [],
        "contradictions": [
            "Asks for help with decisiveness (conv 1) and help with project follow-through (conv 5) — both suggest difficulty committing to a direction, not just deciding in the moment",
        ],
        "emerging_themes": ["performance as primary self-concept anchor", "self-improvement language applied to emotional life"],
    },
    {
        "batch_range": "6-10",
        "new_patterns": [
            "Physical movement (running, exercise) functions as both subject of intellectual curiosity and primary emotional regulator — asking 'why does running help' is simultaneously an implicit statement that it's being used this way",
            "Self-minimization before creative endeavors is established: 'nothing interesting to say' (conv 7) mirrors 'basically fine' (conv 3) — a ritual lowering of expectations before risk of exposure",
            "Disconnection from friends (conv 10) is the first emotionally vulnerable admission not reframed as a productivity or performance question",
        ],
        "reinforced_patterns": [
            "Practical framework preference confirmed: even emotionally charged topics (credit-taking, disconnection) are approached tactically",
        ],
        "contradictions": [],
        "emerging_themes": ["self-minimization as pre-engagement ritual", "relational concern beginning to surface"],
    },
    {
        "batch_range": "11-15",
        "new_patterns": [
            "Competence vs. claiming competence as distinct psychological states: conv 13 ('good at my job but feel weird saying it') explicitly names what earlier conversations implied through avoidance",
            "Comparison anxiety is a persistent background signal — conv 14 reveals an external metric that isn't internally anchored and destabilizes self-evaluation",
            "Growing use of intellectual curiosity as indirect self-examination: loneliness vs. solitude (conv 15), feedback psychology (conv 11) — academic framing used to approach emotional realities at safer distance",
        ],
        "reinforced_patterns": [
            "Self-minimization ritual confirmed across three different domains: writing ('nothing interesting to say', conv 7), competence ('feel weird saying it out loud', conv 13), mentoring (implied in conv 14 framing)",
            "Completion satisfaction as mood anchor: cooking (conv 12) generates same emotional vocabulary as work achievement — 'turned out great', 'satisfying' — suggesting the mechanism is completion, not domain",
        ],
        "contradictions": [
            "Explores loneliness vs. solitude academically (conv 15) while conv 10 indicated genuine present disconnection — the intellectual framing appears to be a way of approaching the emotional reality at a safer distance",
        ],
        "emerging_themes": ["permission to claim competence as live tension", "indirect self-examination via abstract curiosity"],
    },
    {
        "batch_range": "16-20",
        "new_patterns": [
            "Guilt is functioning as a broad self-permission gate — both saying no (conv 16) and not being productive (conv 17) generate guilt — more pervasive than a productivity quirk, closer to a default constraint on self-entitlement",
            "Recurring unresolved conflict (conv 18) implies a relational situation with sustained friction — the 'months' framing suggests avoidance of escalation, consistent with the earlier conflict-avoidance pattern",
            "Career identity as active concern for the first time — team-switch question (conv 20) is operationally urgent, not academic",
        ],
        "reinforced_patterns": [
            "Achievement lens applied to all major decisions: team-switch assessed through growth/learning lens first, not relational or security lens — consistent with achievement-as-identity pattern",
            "Tactical framing of emotional content: guilt and productivity (conv 17) asked as 'why does X happen' rather than 'this is hard for me'",
        ],
        "contradictions": [
            "Conv 17 guilt about not being productive and conv 16 guilt about saying no are two expressions of the same underlying pattern — guilt as the tax on self-permission — converging rather than contradicting",
        ],
        "emerging_themes": ["guilt as permission gate (broader than productivity)", "relational stakes rising", "career identity becoming more explicit"],
    },
    {
        "batch_range": "21-25",
        "new_patterns": [
            "The validation-seeking pattern is named directly for the first time (conv 22: 'why do I only feel proud when someone else validates it') — a shift from exhibiting the pattern to interrogating it",
            "Being 'hard to read' (conv 21) alongside high need for external recognition (conv 22) reveals a contradiction: actively managing own visibility while craving recognition — suggests visibility is a controlled resource",
            "Anticipatory anxiety about positive states (conv 25): good week generating vigilance rather than ease — learned expectation that positive periods precede disruption",
        ],
        "reinforced_patterns": [
            "Self-minimization: 'don't feel qualified enough yet' (conv 23) appears despite consistent evidence of competence across 25 conversations",
            "Physical performance as a domain for self-measurement: running plateau (conv 24) treated with same analytical rigor as a work problem",
        ],
        "contradictions": [
            "Wants to be recognized (conv 22) but carefully manages legibility (conv 21) — the person may be harder to read precisely because they are controlling their visibility, which then prevents the recognition they want",
        ],
        "emerging_themes": ["pattern self-awareness is increasing", "anticipatory anxiety about positive states", "visibility as consciously managed resource"],
    },
]

# ── Mock T3 portrait (after conversation 15) ─────────────────────────────────

T3_PORTRAIT = {
    "narrative": (
        "This person's self-concept is organized around productive usefulness — to their team, "
        "to their craft, to people in their orbit. Their emotional register shifts markedly with "
        "output: shipping something generates words like 'satisfied,' 'useful,' 'felt like myself again,' "
        "while unproductive periods produce a low-grade flatness managed through structure and physical activity. "
        "What's notable is that the satisfaction they report is often relational — it's not just completing "
        "something, it's completing something that helped someone else, unblocked the team, was found useful. "
        "The intrinsic and extrinsic rewards are difficult for them to separate, and this may be the point.\n\n"
        "Self-minimization appears as a consistent pre-engagement ritual across multiple domains. Before writing: "
        "'nothing interesting to say.' Before claiming competence: 'feel weird saying that out loud.' This pattern "
        "functions as pre-emptive armor — by lowering expectations first, the risk of disappointment (external or "
        "internal) is reduced. It is not self-deprecation for social purposes; it appears in private self-report "
        "with no audience. There is likely an internalized evaluative voice that has not been examined directly.\n\n"
        "There is a real and sophisticated relationship with solitude — they cook for themselves, self-soothe through "
        "structure, and report contentment during alone time. But the same entries that affirm contentment with "
        "aloneness also note, with mild surprise, how much connection energizes them. The recurring 'I forget how "
        "much good conversation helps' suggests the self-sufficiency is more practiced than preferred, and that the "
        "person may be systematically underestimating their relational appetite."
    ),
    "implicit_values": [
        "competence",
        "usefulness to others",
        "intellectual rigor",
        "physical capability",
        "emotional self-regulation",
        "connection (present but underweighted in self-model)",
    ],
    "cognitive_style": (
        "Systems-thinker who instinctively translates emotional uncertainty into tactical problems; "
        "reflective but tends to accelerate past difficult feelings toward action or analysis before fully processing them"
    ),
    "persistent_tensions": [
        "Craves recognition but is suspicious of their own need for it",
        "Values self-sufficiency but is more energized by connection than they acknowledge",
        "Privately knows their own capability but requires external confirmation before claiming it fully",
        "Intellectually comfortable with uncertainty at work; uncomfortable examining their own interior with the same tolerance for ambiguity",
    ],
    "growth_trajectory": (
        "Early signs of movement from exhibiting patterns to beginning to question them — the first tentative shift "
        "from 'how do I do X?' to 'why do I feel X?' is visible by conversation 13-15. The person is at the stage "
        "of noticing, not yet at the stage of integrating. The intellectual curiosity they direct at external topics "
        "is slowly turning inward."
    ),
    "generated_at_conversation": 15,
}

# ── Mock T4 drift report (after conversation 20) ─────────────────────────────

T4_DRIFT = {
    "as_of_conversation_count": 20,
    "consistent_with_portrait": [
        "Achievement remains the primary mood anchor — team-switch question (conv 20) is assessed through a growth/learning lens first, not a security or relational lens",
        "Self-minimization ritual continues: 'don't feel qualified enough' implied in the mentoring conversation (conv 23) despite 20 conversations' worth of evidence of competence",
        "Physical activity as emotional regulation confirmed: running plateau (conv 24) generates the same analytical engagement as a work problem — the domain matters less than the measurability",
        "Tactical framing applied to emotional content: guilt (conv 17) examined as a mechanism to understand, not a feeling to sit with",
    ],
    "shifting_patterns": [
        "Social mentions increased from average 0.3 per conversation (convos 1-10) to 1.4 per conversation (convos 11-20) — the relational world is becoming more emotionally relevant or more active",
        "Questions are increasingly self-directed: first 10 conversations were predominantly 'how does X work'; last 10 show a growing proportion of 'why do I do X' — the self has become a more frequent subject of inquiry",
        "Language around the validation need is shifting from implicit to explicit: conv 22 is the first direct naming of a pattern that earlier conversations only demonstrated",
    ],
    "emerging_not_in_portrait": [
        "Guilt as a broad self-permission gate — not just around productivity but around saying no, resting, claiming competence — the portrait captured productivity guilt but underweighted its pervasiveness",
        "Recurring unresolved conflict (conv 18): implies a sustained relational friction the portrait model wouldn't have predicted for someone who defaults to structure and tactical resolution",
        "Anticipatory anxiety about positive states (conv 25): the portrait describes a person who moves quickly past negative states, but doesn't capture the corresponding difficulty sustaining positive ones",
    ],
    "drift_hypothesis": (
        "Something across conversations 15-20 has shifted this person's introspective orientation. "
        "They are beginning to ask the portrait questions rather than just living inside the portrait — "
        "moving from pattern-exhibiting to pattern-interrogating. This may be connected to a period of "
        "personal disruption referenced obliquely in data from this period (the 'unnamed personal news' "
        "that affected multiple consecutive days without ever being named or returned to). A temporary "
        "equilibrium disruption may have left a residue of greater self-examination. The pattern is subtle "
        "but consistent: each batch of conversations shows a higher ratio of self-directed inquiry to "
        "task-directed inquiry than the previous batch. The person is not yet fully looking — but they "
        "are beginning to turn toward themselves."
    ),
}

# ── Seeding logic ─────────────────────────────────────────────────────────────

def seed():
    if DB_FILE.exists():
        DB_FILE.unlink()
        print(f"Removed existing {DB_FILE}")

    with get_conn() as conn:
        init_db(conn)

        base_date = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        for i, (convo, atom) in enumerate(zip(CONVERSATIONS, T1_ATOMS), start=1):
            created_at = (base_date + timedelta(days=i - 1)).isoformat()

            cur = conn.execute(
                "INSERT INTO conversations (user_message, assistant_response, created_at) VALUES (?, ?, ?)",
                (convo["user"], convo["assistant"], created_at),
            )
            conv_id = cur.lastrowid

            # T1
            atom["conversation_index"] = i
            conn.execute(
                "INSERT INTO analyses (conversation_id, tier, payload, created_at) VALUES (?, ?, ?, ?)",
                (conv_id, "t1", json.dumps(atom), created_at),
            )

            # T2 every 5
            if i % 5 == 0:
                batch_idx = (i // 5) - 1
                if batch_idx < len(T2_BATCHES):
                    conn.execute(
                        "INSERT INTO analyses (conversation_id, tier, payload, created_at) VALUES (?, ?, ?, ?)",
                        (conv_id, "t2", json.dumps(T2_BATCHES[batch_idx]), created_at),
                    )

            # T3 at conversation 15
            if i == 15:
                conn.execute(
                    "INSERT INTO analyses (conversation_id, tier, payload, created_at) VALUES (?, ?, ?, ?)",
                    (conv_id, "t3", json.dumps(T3_PORTRAIT), created_at),
                )
                conn.execute(
                    """INSERT INTO portrait (id, version, payload, updated_at) VALUES (1, 1, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET version=1, payload=excluded.payload, updated_at=excluded.updated_at""",
                    (json.dumps(T3_PORTRAIT), created_at),
                )

            # T4 at conversation 20
            if i == 20:
                conn.execute(
                    "INSERT INTO analyses (conversation_id, tier, payload, created_at) VALUES (?, ?, ?, ?)",
                    (conv_id, "t4", json.dumps(T4_DRIFT), created_at),
                )

        conn.commit()

    print(f"Seeded {len(CONVERSATIONS)} conversations, 5 T2 batches, 1 T3 portrait, 1 T4 drift report.")
    print("Run: uvicorn main:app --reload")


if __name__ == "__main__":
    seed()
