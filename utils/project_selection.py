import os


def _filter_visible_dirs(base_dir, current_app_dir=None):
    excluded_names = {"outputs"}
    if current_app_dir:
        app_path = os.path.abspath(current_app_dir)
        app_name = os.path.basename(app_path)
        if app_name:
            excluded_names.add(app_name)
        parent_name = os.path.basename(os.path.dirname(app_path))
        if parent_name:
            excluded_names.add(parent_name)

    visible = []
    for entry in sorted(os.listdir(base_dir)):
        entry_path = os.path.join(base_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if entry.startswith('.'):
            continue
        if entry in excluded_names:
            continue
        visible.append(entry)
    return visible


def get_selectable_project_folders(root_dir, current_app_dir=None, include_all=True):
    """取得可供互動選單使用的分析目錄清單。"""
    if not root_dir:
        return ["all"] if include_all else []

    try:
        folders = _filter_visible_dirs(root_dir, current_app_dir=current_app_dir)
    except Exception:
        return ["all"] if include_all else []

    if include_all:
        return ["all", *folders]
    return folders


def resolve_analysis_target_path(root_dir, selected_folder, current_app_dir=None):
    """解析使用者選擇的分析目標。"""
    if not root_dir:
        return None
    if selected_folder == "all":
        return root_dir
    candidate_path = os.path.join(root_dir, selected_folder)
    if os.path.exists(candidate_path):
        return candidate_path
    if current_app_dir:
        alt_path = os.path.join(os.path.abspath(current_app_dir), selected_folder)
        if os.path.exists(alt_path):
            return alt_path
    return candidate_path


def select_analysis_path(root_dir, current_app_dir=None, prompt_title=None, questionary_module=None):
    """以分層方式讓使用者逐步選擇分析範圍。"""
    if not root_dir:
        return None

    if questionary_module is None:
        try:
            import questionary
            questionary_module = questionary
        except ImportError as exc:
            raise RuntimeError("questionary 未安裝，請先安裝依賴") from exc

    current_dir = os.path.abspath(root_dir)
    while True:
        visible_dirs = _filter_visible_dirs(current_dir, current_app_dir=current_app_dir)
        choices = []
        if current_dir != os.path.abspath(root_dir):
            choices.append("[返回上層]")
        if current_dir == os.path.abspath(root_dir):
            choices.append("[分析整個專案根目錄]")
        else:
            choices.append("[分析此資料夾]")
        choices.extend(visible_dirs)

        if not choices:
            return current_dir

        title = prompt_title or "📂 請選擇要分析的資料夾："
        selected = questionary_module.select(title, choices=choices).ask()
        if selected is None:
            return None

        if selected == "[返回上層]":
            parent_dir = os.path.dirname(current_dir)
            if os.path.exists(parent_dir):
                current_dir = parent_dir
            continue

        if selected in {"[分析此資料夾]", "[分析整個專案根目錄]"}:
            return current_dir

        child_path = os.path.join(current_dir, selected)
        if os.path.isdir(child_path):
            current_dir = child_path
            continue

        return current_dir
