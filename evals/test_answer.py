import asyncio

from evals.answer import ask_unit, units


def reply(status="answered", message="m", options=None):
    answer = {
        "status": status,
        "message": message,
        "rule_verbatim": None,
        "sources": [],
        "options": options or [],
        "reason": None,
    }
    return {"ok": True, "seconds": 1.0, "answer": answer, "verified": answer}


FAILED = {"ok": False, "seconds": 1.0, "error": "ThrottlingException: slow down"}


class Service:
    """Stands in for the model: gives the next reply and keeps what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.asked: list[tuple[str, list[dict]]] = []

    async def __call__(self, question, history):
        self.asked.append((question, [turn.model_dump() for turn in history]))
        return self.replies.pop(0)


def turn(name, number, earlier, question):
    return {"id": f"{name}-t{number}", "earlier": earlier, "question": question}


def run(rows, service):
    return asyncio.run(ask_unit(rows, service))


def test_a_single_question_is_asked_once_with_no_history():
    service = Service(reply())

    records, setup = run([{"id": "G001", "question": "q"}], service)

    assert service.asked == [("q", [])]
    assert [r["question_id"] for r in records] == ["G001"]
    assert "history" not in records[0]
    assert setup == []


def test_turn_2_is_sent_the_answer_the_service_really_gave_to_turn_1():
    service = Service(reply(message="No, not in a public tool."), reply())

    records, setup = run([turn("C17", 2, ["Can I?"], "That's wrong.")], service)

    question, history = service.asked[1]
    assert question == "That's wrong."
    assert history == [
        {
            "question": "Can I?",
            "status": "answered",
            "message": "No, not in a public tool.",
            "options": [],
        }
    ]
    assert [r["question_id"] for r in records] == ["C17-t2"]
    assert records[0]["history"] == history
    assert len(setup) == 1


def test_a_three_turn_conversation_is_asked_three_times_not_five():
    service = Service(reply(message="one"), reply(message="two"), reply())
    rows = [turn("C16", 2, ["a"], "b"), turn("C16", 3, ["a", "b"], "c")]

    records, setup = run(rows, service)

    assert [question for question, _ in service.asked] == ["a", "b", "c"]
    assert [r["question_id"] for r in records] == ["C16-t2", "C16-t3"]
    assert [h["message"] for h in records[1]["history"]] == ["one", "two"]
    assert len(setup) == 1


def test_the_options_offered_on_an_earlier_turn_go_with_it():
    service = Service(
        reply("need_more_detail", "Which?", ["Data", "Security"]), reply()
    )

    run([turn("C12", 2, ["What are the rules?"], "Security.")], service)

    assert service.asked[1][1][0]["options"] == ["Data", "Security"]


def test_a_blocked_turn_is_left_out_of_what_is_sent_next_as_the_front_end_does():
    service = Service(reply(message="one"), reply("blocked", "no"), reply())
    rows = [turn("C14", 2, ["a"], "b"), turn("C14", 3, ["a", "b"], "c")]

    records, _ = run(rows, service)

    assert [h["question"] for h in records[1]["history"]] == ["a"]


def test_only_the_last_four_turns_are_sent():
    service = Service(*(reply(message=str(n)) for n in range(6)))

    records, _ = run([turn("C99", 6, list("abcde"), "f")], service)

    assert [h["question"] for h in records[0]["history"]] == list("bcde")


def test_a_long_answer_is_cut_to_what_the_front_end_sends():
    service = Service(reply(message="x" * 2500), reply())

    records, _ = run([turn("C1", 2, ["a"], "b")], service)

    assert len(records[0]["history"][0]["message"]) == 2000


def test_when_an_earlier_turn_fails_the_later_turns_are_failures_and_are_not_asked():
    service = Service(FAILED)
    rows = [turn("C16", 2, ["a"], "b"), turn("C16", 3, ["a", "b"], "c")]

    records, _ = run(rows, service)

    assert len(service.asked) == 1
    assert [r["ok"] for r in records] == [False, False]
    assert "turn 1" in records[0]["error"]


def test_asking_for_turn_3_alone_still_asks_the_turns_before_it():
    service = Service(reply(), reply(), reply())

    records, setup = run([turn("C16", 3, ["a", "b"], "c")], service)

    assert [question for question, _ in service.asked] == ["a", "b", "c"]
    assert [r["question_id"] for r in records] == ["C16-t3"]
    assert len(setup) == 2


def test_a_run_that_reaches_its_ceiling_stops_the_conversation():
    service = Service(reply(), None)
    rows = [turn("C16", 2, ["a"], "b"), turn("C16", 3, ["a", "b"], "c")]

    records, _ = run(rows, service)

    assert records == []
    assert len(service.asked) == 2


def test_a_conversations_turns_are_kept_together_and_singles_stay_apart():
    questions = [
        {"id": "G001"},
        {"id": "G002"},
        {"id": "C16-t2"},
        {"id": "C17-t2"},
        {"id": "C16-t3"},
    ]

    grouped = [[q["id"] for q in unit] for unit in units(questions)]

    assert grouped == [["G001"], ["G002"], ["C16-t2", "C16-t3"], ["C17-t2"]]
