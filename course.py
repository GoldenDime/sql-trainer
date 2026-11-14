"""Сборка курса."""
import course_analytics
import course_base

MODULES = course_base.MODULES + course_analytics.MODULES
TASKS = {t['id']: t for m in MODULES for t in m['tasks']}
ORDER = [t['id'] for m in MODULES for t in m['tasks']]
