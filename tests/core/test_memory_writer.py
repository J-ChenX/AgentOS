class TestReplaceSection:
    def test_replaces_existing_section(self, tmp_path):
        md = tmp_path / "memory.md"
        md.write_text(
            "# 核心记忆\n\n## 用户偏好\n\n旧内容\n\n## 项目规范\n\n规范内容\n",
            encoding="utf-8",
        )
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(md), section_title="用户偏好", new_content="喜欢深色主题\n"
        )
        assert "成功" in result
        content = md.read_text(encoding="utf-8")
        assert "喜欢深色主题" in content
        assert "旧内容" not in content
        # 下一个 section 保持不变
        assert "## 项目规范" in content
        assert "规范内容" in content

    def test_replaces_last_section(self, tmp_path):
        md = tmp_path / "memory.md"
        md.write_text(
            "# 核心记忆\n\n## 用户偏好\n\n偏好\n\n## 知识库索引\n\n旧索引\n",
            encoding="utf-8",
        )
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(md), section_title="知识库索引", new_content="新索引条目\n"
        )
        assert "成功" in result
        content = md.read_text(encoding="utf-8")
        assert "新索引条目" in content
        assert "旧索引" not in content
        assert "## 用户偏好" in content

    def test_section_not_found(self, tmp_path):
        md = tmp_path / "memory.md"
        md.write_text("# 核心记忆\n\n## 用户偏好\n\n内容\n", encoding="utf-8")
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(md), section_title="不存在的分区", new_content="内容"
        )
        assert "未找到" in result

    def test_does_not_match_h3_headings(self, tmp_path):
        md = tmp_path / "memory.md"
        md.write_text(
            "# 核心记忆\n\n## 用户偏好\n\n### 子标题\n\n子内容\n\n## 项目规范\n\n规范\n",
            encoding="utf-8",
        )
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(md), section_title="用户偏好", new_content="新偏好\n"
        )
        assert "成功" in result
        content = md.read_text(encoding="utf-8")
        assert "新偏好" in content
        assert "子内容" not in content
        assert "## 项目规范" in content

    def test_skips_h2_inside_code_blocks(self, tmp_path):
        md = tmp_path / "memory.md"
        md.write_text(
            "# 核心记忆\n\n## 用户偏好\n\n"
            "```\n## 这不是标题\n```\n\n偏好内容\n\n## 项目规范\n\n规范\n",
            encoding="utf-8",
        )
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(md), section_title="用户偏好", new_content="新偏好\n"
        )
        assert "成功" in result
        content = md.read_text(encoding="utf-8")
        assert "新偏好" in content
        assert "这不是标题" not in content
        assert "## 项目规范" in content

    def test_file_not_found(self, tmp_path):
        from agentos.builtin_skills.memory_writer.skill import replace_section

        result = replace_section(
            file_path=str(tmp_path / "nonexistent.md"),
            section_title="foo",
            new_content="bar",
        )
        assert "不存在" in result


class TestAppendToFile:
    def test_appends_to_existing_file(self, tmp_path):
        md = tmp_path / "store" / "bugs.md"
        md.parent.mkdir()
        md.write_text("# Bug 记录\n\n旧记录\n", encoding="utf-8")
        from agentos.builtin_skills.memory_writer.skill import append_to_file

        result = append_to_file(file_path=str(md), content="\n## Bug #2\n\n新 bug\n")
        assert "成功" in result
        content = md.read_text(encoding="utf-8")
        assert "旧记录" in content
        assert "新 bug" in content

    def test_creates_file_and_parent_dirs(self, tmp_path):
        md = tmp_path / "memory_store" / "new_topic.md"
        from agentos.builtin_skills.memory_writer.skill import append_to_file

        result = append_to_file(file_path=str(md), content="# 新主题\n\n内容\n")
        assert "成功" in result or "创建" in result
        assert md.exists()
        assert "新主题" in md.read_text(encoding="utf-8")

    def test_empty_content_rejected(self, tmp_path):
        from agentos.builtin_skills.memory_writer.skill import append_to_file

        result = append_to_file(file_path=str(tmp_path / "test.md"), content="")
        assert "空" in result or "内容不能为空" in result
