"""Seed initial data: demo user, sample stories with episodes/choices, and a quiz-like episode.

Revision ID: 0003_seed_initial_data
Revises: 0002_initial_schema
Create Date: 2025-01-01 00:20:00

"""
from alembic import op
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "0003_seed_initial_data"
down_revision = "0002_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Insert stories
    stories = [
        ("Leadership Basics", "A short scenario to practice leadership decision-making. Tags: leadership"),
        ("Effective Communication", "Navigate a tough stakeholder update meeting. Tags: communication"),
        ("Emotional Intelligence at Work", "Handle a teammate's frustration during a sprint. Tags: emotional-intelligence"),
        ("Team Decision-Making", "Facilitate alignment on a technical approach. Tags: leadership, communication"),
    ]
    story_ids = {}

    for title, desc in stories:
        result = conn.execute(
            text('SELECT id FROM "story" WHERE title=:title'),
            {"title": title},
        ).first()
        if result:
            story_id = result[0]
        else:
            story_id = conn.execute(
                text('INSERT INTO "story"(title, description) VALUES (:t, :d) RETURNING id'),
                {"t": title, "d": desc},
            ).scalar_one()
        story_ids[title] = story_id

    # Leadership Basics episodes and choices
    s = story_ids["Leadership Basics"]
    ep0 = _ensure_episode(conn, s, 0, "You are leading a new project kickoff. How do you start?")
    _ensure_choice(conn, ep0, "Listen to the team's input", 1, 10)
    _ensure_choice(conn, ep0, "Present a detailed plan immediately", 2, 5)

    ep1 = _ensure_episode(conn, s, 1, "You choose to listen first. The team shares concerns.")
    _ensure_choice(conn, ep1, "Acknowledge concerns and co-create next steps", None, 15)

    ep2 = _ensure_episode(conn, s, 2, "You choose to assert a plan. The team seems hesitant.")
    _ensure_choice(conn, ep2, "Invite feedback to adjust the plan", None, 10)

    # Effective Communication
    s = story_ids["Effective Communication"]
    ec0 = _ensure_episode(conn, s, 0, "The product launch is delayed. How do you open the stakeholder meeting?")
    _ensure_choice(conn, ec0, "Start with transparency about risks and status", 1, 10)
    _ensure_choice(conn, ec0, "Highlight positives and defer the delay conversation", 2, 5)
    _ensure_choice(conn, ec0, "Ask stakeholders for their priorities before sharing status", 1, 8)
    ec1 = _ensure_episode(conn, s, 1, "Stakeholders appreciate the clarity. They ask for impact and next steps.")
    _ensure_choice(conn, ec1, "Share a concise impact summary and a mitigation plan", 3, 15)
    _ensure_choice(conn, ec1, "Promise to follow up later via email", 3, 5)
    ec2 = _ensure_episode(conn, s, 2, "Stakeholders look surprised when the delay surfaces later.")
    _ensure_choice(conn, ec2, "Apologize for the approach and reset with clear facts", 3, 10)
    _ensure_choice(conn, ec2, "Continue focusing on positives only", None, 2)
    ec3 = _ensure_episode(conn, s, 3, "Meeting wrap-up: stakeholders want a weekly update cadence.")
    _ensure_choice(conn, ec3, "Confirm a brief weekly status format", None, 12)
    _ensure_choice(conn, ec3, "Suggest ad-hoc updates only", None, 3)

    # Emotional Intelligence
    s = story_ids["Emotional Intelligence at Work"]
    ei0 = _ensure_episode(conn, s, 0, "A teammate is visibly frustrated after feedback on their code. What do you do first?")
    _ensure_choice(conn, ei0, "Privately ask how they are feeling and listen", 1, 12)
    _ensure_choice(conn, ei0, "Remind them to be professional and move on", 2, 3)
    ei1 = _ensure_episode(conn, s, 1, "They share they're overwhelmed. They fear missing expectations.")
    _ensure_choice(conn, ei1, "Validate feelings and ask what support would help", 3, 15)
    _ensure_choice(conn, ei1, "Offer to pair-program on a problem area", 3, 10)
    ei2 = _ensure_episode(conn, s, 2, "They quiet down, but the tension remains.")
    _ensure_choice(conn, ei2, "Revisit the conversation later with empathy", 3, 8)
    _ensure_choice(conn, ei2, "Ignore it and focus on sprint tasks", None, 1)
    ei3 = _ensure_episode(conn, s, 3, "You agree on a plan to adjust workload and checkpoints.")
    _ensure_choice(conn, ei3, "Summarize the plan and schedule a follow-up", None, 12)
    _ensure_choice(conn, ei3, "Leave it informal with no clear next step", None, 4)

    # Team Decision-Making with a quiz-style question as episode 1
    s = story_ids["Team Decision-Making"]
    td0 = _ensure_episode(
        conn,
        s,
        0,
        "Two engineers disagree on architecture. How do you begin?")
    _ensure_choice(conn, td0, "Set a clear decision-making framework", 1, 12)
    _ensure_choice(conn, td0, "Let them debate freely and hope it resolves", 2, 4)
    td1 = _ensure_episode(
        conn,
        s,
        1,
        "QUIZ: Which criteria is LEAST important to settle first? (A) Scalability (B) Timeline (C) Personal Preference",
    )
    # Treat as choices with xp-gain like quiz correctness (C is least important)
    _ensure_choice(conn, td1, "A) Scalability", 3, 5)
    _ensure_choice(conn, td1, "B) Timeline", 3, 5)
    _ensure_choice(conn, td1, "C) Personal Preference", 3, 12)  # 'correct' answer rewards more XP
    td2 = _ensure_episode(conn, s, 2, "Debate is heated and unfocused.")
    _ensure_choice(conn, td2, "Refocus on criteria and timebox discussion", 3, 10)
    _ensure_choice(conn, td2, "End the meeting without a decision", None, 1)
    td3 = _ensure_episode(conn, s, 3, "Team converges on a pragmatic option with a revisit checkpoint.")
    _ensure_choice(conn, td3, "Document the decision and owners", None, 12)
    _ensure_choice(conn, td3, "Move on without documenting rationale", None, 3)

    # Demo user
    demo = conn.execute(text('SELECT id FROM "user" WHERE username=:u'), {"u": "demo_user"}).first()
    if not demo:
        demo_id = conn.execute(
            text(
                'INSERT INTO "user"(username, display_name, is_active, xp) VALUES (:u, :d, true, 0) RETURNING id'
            ),
            {"u": "demo_user", "d": "Demo User"},
        ).scalar_one()
        # set initial progress to Leadership Basics ep 0
        lb_id = story_ids["Leadership Basics"]
        conn.execute(
            text('UPDATE "user" SET current_story_id=:sid, current_episode_index=:idx WHERE id=:uid'),
            {"sid": lb_id, "idx": 0, "uid": demo_id},
        )


def _ensure_episode(conn, story_id: int, index: int, content: str) -> int:
    row = conn.execute(
        text('SELECT id, content FROM "episode" WHERE story_id=:sid AND "index"=:idx'),
        {"sid": story_id, "idx": index},
    ).first()
    if row:
        ep_id, existing = row
        if existing != content:
            conn.execute(text('UPDATE "episode" SET content=:c WHERE id=:id'), {"c": content, "id": ep_id})
        return ep_id
    return conn.execute(
        text('INSERT INTO "episode"(story_id, "index", content) VALUES (:sid, :idx, :c) RETURNING id'),
        {"sid": story_id, "idx": index, "c": content},
    ).scalar_one()


def _ensure_choice(conn, episode_id: int, text_value: str, next_index: int | None, xp: int) -> int:
    row = conn.execute(
        text('SELECT id, next_episode_index, xp_delta FROM "choice" WHERE episode_id=:eid AND text=:t'),
        {"eid": episode_id, "t": text_value},
    ).first()
    if row:
        ch_id, next_ep, xp_delta = row
        updates = []
        params = {"id": ch_id}
        if next_ep != next_index:
            updates.append("next_episode_index=:n")
            params["n"] = next_index
        if xp_delta != xp:
            updates.append("xp_delta=:x")
            params["x"] = xp
        if updates:
            conn.execute(text(f'UPDATE "choice" SET {", ".join(updates)} WHERE id=:id'), params)
        return ch_id
    return conn.execute(
        text(
            'INSERT INTO "choice"(episode_id, text, next_episode_index, xp_delta) '
            'VALUES (:eid, :t, :n, :x) RETURNING id'
        ),
        {"eid": episode_id, "t": text_value, "n": next_index, "x": xp},
    ).scalar_one()


def downgrade() -> None:
    # For simplicity, do not remove seeded data on downgrade.
    pass
