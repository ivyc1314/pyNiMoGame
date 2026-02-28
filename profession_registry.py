from dataclasses import dataclass


@dataclass(frozen=True)
class ProfessionDef:
    id: str
    label: str
    intro_lines: tuple[str, ...]
    skill_id: str
    icon_stem: str


_PROFESSION_ORDER = ("paladin", "swordsman", "thief", "blacksmith")
_DEFAULT_PROFESSION = "paladin"
_PROFESSION_REGISTRY: dict[str, ProfessionDef] = {
    "paladin": ProfessionDef(
        id="paladin",
        label="\u5723\u9a91\u58eb",
        intro_lines=(
            "\u5b9a\u4f4d\uff1a\u7a33\u5065\u9632\u5b88",
            "\u6280\u80fd\u3010\u5723\u76fe\u3011\uff1a\u7ed9\u4e00\u679a\u5b8c\u6574\u68cb\u5b50\u52a0\u62a4\u76fe",
            "\u62a4\u76fe\u6301\u7eed\u4e24\u4e2a\u56de\u5408\uff0c\u751f\u6548\u671f\u95f4\u53ef\u62b5\u63211\u6b21\u79fb\u9664",
        ),
        skill_id="shield",
        icon_stem="\u5723\u9a91\u58eb\u6807\u5fd7",
    ),
    "swordsman": ProfessionDef(
        id="swordsman",
        label="\u5251\u5ba2",
        intro_lines=(
            "\u5b9a\u4f4d\uff1a\u5f3a\u52bf\u8fdb\u653b",
            "\u6280\u80fd\u3010\u5341\u5b57\u65a9\u3011\uff1a\u4ee5\u76ee\u6807\u4e3a\u4e2d\u5fc3\u5c55\u5f00",
            "\u53ef\u4e00\u6b21\u6e05\u9664\u6a2a\u5411\u4e0e\u7eb5\u5411\u76ee\u6807",
        ),
        skill_id="cross",
        icon_stem="\u5251\u5ba2\u6807\u5fd7",
    ),
    "thief": ProfessionDef(
        id="thief",
        label="\u76d7\u8d3c",
        intro_lines=(
            "\u5b9a\u4f4d\uff1a\u7075\u6d3b\u63a7\u573a",
            "\u6280\u80fd\u3010\u6697\u624b\u3011\uff1a\u9009\u62e9\u4e00\u4e2a\u4ecd\u7136\u5b58\u5728\u7684\u68cb\u5b50",
            "\u53ef\u4e0e\u4efb\u610f\u5b8c\u6574/\u7834\u788e\u68cb\u4f4d\u4ea4\u6362\uff0c\u4e5f\u53ef\u79fb\u5230\u884c\u5c3e\u65b0\u589e\u69fd\u4f4d",
        ),
        skill_id="shadow_hand",
        icon_stem="\u76d7\u8d3c\u6807\u5fd7",
    ),
    "blacksmith": ProfessionDef(
        id="blacksmith",
        label="\u94c1\u5320",
        intro_lines=(
            "\u5b9a\u4f4d\uff1a\u533a\u57df\u5c01\u9501",
            "\u6280\u80fd\u3010\u5d4c\u6761\u3011\uff1a\u53ef\u5728\u540c\u6392\u76f8\u90bb\u4e24\u683c\u95f4\u843d\u4e0b\u94c1\u6761",
            "\u94c1\u6761\u5728\u672c\u5c40\u6c38\u4e45\u5b58\u5728\uff0c\u963b\u6b62\u4efb\u4f55\u8de8\u8d8a\u94c1\u6761\u7684\u65a9\u51fb",
        ),
        skill_id="inlay_bar",
        icon_stem="\u5de5\u7a0b\u5e08\u56fe\u6807",
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
