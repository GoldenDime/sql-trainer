"""Сборка теории: страницы по модулям."""
import theory_analytics
import theory_core
import theory_more

PAGES = {}
for _m in (theory_core, theory_more, theory_analytics):
    PAGES.update(_m.PAGES)


def pages(mid):
    return PAGES.get(mid, [])
