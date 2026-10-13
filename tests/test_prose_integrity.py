from rcwh.generation.prose_integrity import prose_integrity


def test_numeric_counter_changes_cannot_hide_repeated_padding():
    sentence = "平儿将钥匙重新系紧，绳结太短，拆开一次便要重新打。这是第{}次清点后的细小阻滞，仍需下一只手来接。"
    text = "\n\n".join(sentence.format(i) for i in range(1, 13))
    report = prose_integrity(text)
    assert report["status"] == "FAIL"
    assert report["clusters"][0]["occurrences"] == 12
    assert report["repeated_character_fraction"] > .8
    assert report["literary_quality_verified"] is False


def test_normal_motifs_and_brief_dialogue_refrains_are_not_rejected():
    text = "平儿重新系紧钥匙，听见外面有人唤她，便停下针线。\n\n她应道：知道了。\n\n宝钗收起米升，给孩子另盛了小半碗。\n\n她应道：知道了。\n\n门外的人又催了一声。\n\n她应道：知道了。"
    assert prose_integrity(text)["status"] == "PASS"


def test_small_long_refrain_is_only_a_warning():
    refrain = "门外的脚步走过，屋里人仍没有拿起那张未写完的纸，等候并没有使所有事情一时变得明白。"
    other = "\n\n".join(f"第{i}场的人说了不同的话，话里带着{i}件真正不同的事情。" + "别处的日常尚未收束。" * i for i in range(10, 20))
    assert prose_integrity(other + "\n\n" + "\n\n".join([refrain] * 3))["status"] == "WARN"


def test_generation_script_is_not_chapter_prose():
    text = "宝玉端起碗，却听门外叫他。\n\nexpanded=[]\nfor i,p in enumerate(paras):\n expanded.append(p)\nprint('FROZEN', p)\nPY"
    report = prose_integrity(text)
    assert report["status"] == "FAIL"
    assert "GENERATION_SCRIPT_LEAKED_IN_PROSE" in report["findings"]


def test_chinese_characters_named_for_and_import_are_not_python():
    assert prose_integrity("她问所谓入口为何，他没有回答，又把门闩放下。\n\n这个import字样是纸上的英文，倒不像屋里人说的话。")["status"] == "PASS"
