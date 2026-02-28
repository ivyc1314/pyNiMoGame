from dataclasses import dataclass


@dataclass(frozen=True)
class ProfessionDef:
    id: str
    label: str
    intro_lines: tuple[str, ...]
    skill_id: str
    icon_stem: str


_PROFESSION_ORDER = ("paladin", "swordsman")
_DEFAULT_PROFESSION = "paladin"
_PROFESSION_REGISTRY: dict[str, ProfessionDef] = {
    "paladin": ProfessionDef(
        id="paladin",
        label="圣骑士",
        intro_lines=(
            "定位：稳健防守",
            "技能【圣盾】：给1枚完整棋子加护盾",
            "护盾生效期间可抵挡1次移除",
        ),
        skill_id="shield",
        icon_stem="圣骑士标志",
    ),
    "swordsman": ProfessionDef(
        id="swordsman",
        label="剑客",
        intro_lines=(
            "定位：强势进攻",
            "技能【十字斩】：以目标为中心展开",
            "可一次清除横向与纵向目标",
        ),
        skill_id="cross",
        icon_stem="剑客标志",
    ),
}


def get_profession_ids() -> list[str]:
    return list(_PROFESSION_ORDER)


def get_default_profession() -> str:
    return _DEFAULT_PROFESSION


def get_profession(profession_id: str) -> ProfessionDef:
    if profession_id in _PROFESSION_REGISTRY:
        return _PROFESSION_REGISTRY[profession_id]
    return _PROFESSION_REGISTRY[_DEFAULT_PROFESSION]


def get_profession_label(profession_id: str) -> str:
    return get_profession(profession_id).label


def get_profession_intro_lines(profession_id: str) -> list[str]:
    return list(get_profession(profession_id).intro_lines)


def get_profession_skill_id(profession_id: str) -> str:
    return get_profession(profession_id).skill_id


def get_profession_icon_stem(profession_id: str) -> str:
    return get_profession(profession_id).icon_stem
