import os


def get_selectable_project_folders(root_dir, current_app_dir=None, include_all=True):
    """取得可供互動選單使用的分析目錄清單。"""
    if not root_dir:
        return ["all"] if include_all else []

    excluded_names = {"outputs"}
    if current_app_dir:
        app_path = os.path.abspath(current_app_dir)
        app_name = os.path.basename(app_path)
        if app_name:
            excluded_names.add(app_name)
        if os.path.dirname(app_path):
            excluded_names.add(os.path.basename(os.path.dirname(app_path)))

    folders = []
    try:
        for entry in sorted(os.listdir(root_dir)):
            entry_path = os.path.join(root_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith('.'):
                continue
            if entry in excluded_names:
                continue
            if current_app_dir and entry.lower() == os.path.basename(os.path.abspath(current_app_dir)).lower():
                continue
            folders.append(entry)
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
