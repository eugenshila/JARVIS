"""Business Tools — Manage goals, priorities, workflows, rules, standards, business profile.

These tools teach JARVIS your business — persistent memory + business_profile.toml
"""

from __future__ import annotations

from jarvis.tools.base import BaseTool
from jarvis.core.business_profile import get_business_profile, BusinessProfile
from jarvis.core.config import get_home
import json

class BusinessProfileTool(BaseTool):
    name = "business_profile"
    description = "Show or update business profile — goals, priorities, business, workflows, rules, standards. The brain of Business OS."
    
    def run(self, action: str = "show", **kwargs) -> str:
        profile = get_business_profile()
        
        if action == "show" or action == "view" or action == "list":
            return profile.to_context() + f"\n\nFile: {profile.path}\nJSON: {profile.json_path}\n\nUse action=edit to update. SHILATECH • Malibu Point 10880"
        
        if action == "path":
            return f"Business profile TOML: {profile.path}\nJSON: {profile.json_path}\nHome: {get_home()}\nExists: {profile.path.exists()}"
        
        if action == "reset":
            # Reset to defaults and save
            new_profile = BusinessProfile()
            new_profile.save()
            return f"Business profile reset to defaults, Sir. Saved to {new_profile.path}\n\n{new_profile.to_context()}"
        
        if action == "edit":
            # Update from kwargs
            from datetime import datetime
            updated = []
            if "north_star" in kwargs:
                profile.goals.north_star = kwargs["north_star"]
                updated.append(f"North Star: {kwargs['north_star']}")
            if "user_name" in kwargs:
                profile.user_name = kwargs["user_name"]
                updated.append(f"User: {kwargs['user_name']}")
            if "business_name" in kwargs:
                profile.business.name = kwargs["business_name"]
                updated.append(f"Business: {kwargs['business_name']}")
            if "mission" in kwargs:
                profile.business.mission = kwargs["mission"]
                updated.append(f"Mission: {kwargs['mission']}")
            if updated:
                profile.updated_at = datetime.now().isoformat()
                profile.save()
                return f"Updated, Sir:\n" + "\n".join(updated) + f"\n\nSaved to {profile.path}\n\n{profile.to_context()}"
            else:
                return f"No updates provided. Use: north_star, user_name, business_name, mission. Current:\n{profile.to_context()}"
        
        return f"Unknown action {action}. Use: show, path, reset, edit. Current:\n{profile.to_context()}"

class BusinessGoalsTool(BaseTool):
    name = "business_goals"
    description = "Manage goals — north star, long term 1Y, short term 90D/30D, personal. Teaches JARVIS your goals."
    
    def run(self, action: str = "show", goal: str = "", timeframe: str = "90d", **kwargs) -> str:
        profile = get_business_profile()
        
        if action == "show" or action == "list":
            return f"""**Goals — {profile.user_name}, Sir — {profile.business.name}**

**North Star:** {profile.goals.north_star}

**Long Term 1Y:**
""" + "\n".join([f"- {g}" for g in profile.goals.long_term_1y]) + f"""

**Short Term 90D:**
""" + "\n".join([f"- {g}" for g in profile.goals.short_term_90d]) + f"""

**Short Term 30D:**
""" + "\n".join([f"- {g}" for g in profile.goals.short_term_30d]) + f"""

**Personal:**
""" + "\n".join([f"- {g}" for g in profile.goals.personal]) + f"""

File: {profile.path}

Use action=add to add goal, action=set_north_star to set north star.
"""
        
        if action == "add":
            if not goal:
                return "Provide goal=Your goal text and timeframe=1y/90d/30d/personal"
            from datetime import datetime
            if timeframe == "1y":
                profile.goals.long_term_1y.append(goal)
            elif timeframe == "90d":
                profile.goals.short_term_90d.append(goal)
            elif timeframe == "30d":
                profile.goals.short_term_30d.append(goal)
            elif timeframe == "personal":
                profile.goals.personal.append(goal)
            else:
                profile.goals.short_term_90d.append(goal)
            
            # Save to memory too
            try:
                from jarvis.memory.store import MemoryStore
                store = MemoryStore()
                store.add(f"Goal {timeframe}: {goal}", {"type": "goal", "timeframe": timeframe})
            except:
                pass
            
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            return f"Added goal to {timeframe}, Sir: {goal}\n\nSaved to {profile.path} + memory store."
        
        if action == "set_north_star":
            if not goal:
                return "Provide goal=Your north star"
            from datetime import datetime
            profile.goals.north_star = goal
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            try:
                from jarvis.memory.store import MemoryStore
                store = MemoryStore()
                store.add(f"North Star: {goal}", {"type": "goal", "timeframe": "north_star"})
            except:
                pass
            return f"North Star set, Sir: {goal}\n\nSaved to {profile.path} + memory."
        
        return f"Unknown action {action}. Use: show, add, set_north_star. Provide goal= and timeframe=1y/90d/30d/personal"

class BusinessPrioritiesTool(BaseTool):
    name = "business_priorities"
    description = "Manage priorities — MITs today, Eisenhower matrix, business pillars. Teaches JARVIS your priorities."
    
    def run(self, action: str = "show", priority: str = "", **kwargs) -> str:
        profile = get_business_profile()
        
        if action == "show":
            return f"""**Priorities — {profile.user_name}, Sir — Today**

**3 MITs Today (Most Important Tasks):**
""" + "\n".join([f"{i+1}. {mit}" for i, mit in enumerate(profile.priorities.mit_today)]) + f"""

**Urgent Important (Do Now):**
""" + "\n".join([f"- {p}" for p in profile.priorities.urgent_important]) + f"""

**Important Not Urgent (Schedule):**
""" + "\n".join([f"- {p}" for p in profile.priorities.important_not_urgent]) + f"""

**Business Pillars:**
""" + "\n".join([f"- {p}" for p in profile.priorities.pillars]) + f"""

Use action=set_mits with priority=MIT1,MIT2,MIT3 to set today's MITs.
"""
        
        if action == "set_mits":
            if not priority:
                return "Provide priority=MIT1,MIT2,MIT3 comma separated"
            mits = [m.strip() for m in priority.split(",") if m.strip()]
            from datetime import datetime
            profile.priorities.mit_today = mits[:3]
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            try:
                from jarvis.memory.store import MemoryStore
                store = MemoryStore()
                for mit in mits[:3]:
                    store.add(f"MIT Today: {mit}", {"type": "priority", "mit": True})
            except:
                pass
            return f"MITs set, Sir:\n" + "\n".join([f"{i+1}. {m}" for i, m in enumerate(mits[:3])]) + f"\n\nSaved to {profile.path} + memory."
        
        if action == "add_pillar":
            if not priority:
                return "Provide priority=Pillar name"
            from datetime import datetime
            profile.priorities.pillars.append(priority)
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            return f"Pillar added, Sir: {priority}\n\nSaved."
        
        return f"Unknown action {action}. Use: show, set_mits, add_pillar"

class BusinessWorkflowsTool(BaseTool):
    name = "business_workflows"
    description = "Manage workflows — daily routine, weekly review, SOPs development and business. Teaches JARVIS your workflows."
    
    def run(self, action: str = "show", workflow: str = "", **kwargs) -> str:
        profile = get_business_profile()
        
        if action == "show":
            return f"""**Workflows — {profile.business.name} — {profile.user_name}, Sir**

**Daily Routine:**
""" + "\n".join([f"- {w}" for w in profile.workflows.daily_routine]) + f"""

**Weekly Review:**
""" + "\n".join([f"- {w}" for w in profile.workflows.weekly_review]) + f"""

**SOP Development (SHILATECH Standard):**
""" + "\n".join([f"{i+1}. {w}" for i, w in enumerate(profile.workflows.sop_development)]) + f"""

**SOP Business:**
""" + "\n".join([f"- {w}" for w in profile.workflows.sop_business]) + f"""

Use action=add with workflow=Your workflow and type=daily/weekly/sop_dev/sop_biz
"""
        
        if action == "add":
            if not workflow:
                return "Provide workflow=Your workflow text and type=daily/weekly/sop_dev/sop_biz"
            wf_type = kwargs.get("type", "daily")
            from datetime import datetime
            if wf_type == "daily":
                profile.workflows.daily_routine.append(workflow)
            elif wf_type == "weekly":
                profile.workflows.weekly_review.append(workflow)
            elif wf_type == "sop_dev":
                profile.workflows.sop_development.append(workflow)
            elif wf_type == "sop_biz":
                profile.workflows.sop_business.append(workflow)
            else:
                profile.workflows.daily_routine.append(workflow)
            
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            return f"Workflow added to {wf_type}, Sir: {workflow}\n\nSaved to {profile.path}"
        
        return f"Unknown action {action}. Use: show, add"

class BusinessRulesTool(BaseTool):
    name = "business_rules"
    description = "Manage rules and standards — coding standards, business rules, communication, decision framework. Teaches JARVIS your rules."
    
    def run(self, action: str = "show", rule: str = "", **kwargs) -> str:
        profile = get_business_profile()
        
        if action == "show":
            return f"""**Rules & Standards — SHILATECH — {profile.user_name}, Sir**

**Coding Standards:**
""" + "\n".join([f"- {r}" for r in profile.rules.coding_standards]) + f"""

**Business Rules:**
""" + "\n".join([f"- {r}" for r in profile.rules.business_rules]) + f"""

**Communication:**
""" + "\n".join([f"- {r}" for r in profile.rules.communication]) + f"""

**Decision Framework:**
""" + "\n".join([f"{i+1}. {r}" for i, r in enumerate(profile.rules.decision_framework)]) + f"""

Use action=add with rule=Your rule and type=coding/business/communication/decision
"""
        
        if action == "add":
            if not rule:
                return "Provide rule=Your rule and type=coding/business/communication/decision"
            r_type = kwargs.get("type", "business")
            from datetime import datetime
            if r_type == "coding":
                profile.rules.coding_standards.append(rule)
            elif r_type == "business":
                profile.rules.business_rules.append(rule)
            elif r_type == "communication":
                profile.rules.communication.append(rule)
            elif r_type == "decision":
                profile.rules.decision_framework.append(rule)
            else:
                profile.rules.business_rules.append(rule)
            
            profile.updated_at = datetime.now().isoformat()
            profile.save()
            try:
                from jarvis.memory.store import MemoryStore
                store = MemoryStore()
                store.add(f"Business Rule {r_type}: {rule}", {"type": "rule", "rule_type": r_type})
            except:
                pass
            return f"Rule added to {r_type}, Sir: {rule}\n\nSaved to {profile.path} + memory."
        
        return f"Unknown action {action}. Use: show, add"

class BusinessMemoryTool(BaseTool):
    name = "business_memory"
    description = "Business persistent memory — save and search business context with vector search. Gives JARVIS persistent memory."
    
    def run(self, action: str = "search", query: str = "", content: str = "", **kwargs) -> str:
        from jarvis.memory.store import MemoryStore
        store = MemoryStore()
        
        if action == "save" or action == "add" or action == "remember":
            if not content and not query:
                return "Provide content=What to remember or query=What to remember"
            text = content or query
            # Add metadata for business
            metadata = {"type": "business_memory", "source": "business_os"}
            if "goal" in kwargs:
                metadata["goal"] = True
            if "workflow" in kwargs:
                metadata["workflow"] = True
            entry = store.add(text, metadata)
            return f"Saved to persistent memory, Sir — ID {entry.id}: {text}\n\nMemory now has {store.stats().get('count', 'N/A')} entries. Vector search enabled if FAISS installed."
        
        if action == "search" or action == "find":
            if not query and not content:
                return "Provide query=What to search"
            q = query or content
            results = store.search(q, top_k=kwargs.get("top_k", 5))
            if not results:
                return f"No memories found for '{q}', Sir. Try adding via action=save content=..."
            out = f"**Found {len(results)} memories for '{q}', Sir:**\n\n"
            for r in results:
                out += f"- **Score {r.score:.2f}** | {r.entry.id}: {r.content[:200]}\n"
            return out
        
        if action == "list":
            limit = kwargs.get("limit", 20)
            entries = store.list(limit=limit)
            if not entries:
                return "No memories yet, Sir. Use action=save content=Your business context"
            out = f"**Last {len(entries)} memories, Sir:**\n\n"
            for e in entries[-limit:]:
                out += f"- {e.id}: {e.content[:150]}\n"
            return out
        
        if action == "stats":
            stats = store.stats()
            return f"**Memory Stats, Sir:**\n\n{json.dumps(stats, indent=2)}\n\nLocation: {get_home() / 'memory'}"
        
        if action == "clear":
            confirm = kwargs.get("confirm", False)
            if not confirm:
                return "To clear memory, use action=clear confirm=True — This deletes all memories, Sir!"
            store.clear()
            return "Memory cleared, Sir. All business context deleted."
        
        return f"Unknown action {action}. Use: save, search, list, stats, clear. Query/content required for save/search."
