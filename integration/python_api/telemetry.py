from __future__ import annotations

import json
from collections import defaultdict
from collections import Counter
from pathlib import Path
import re
from threading import Lock
from uuid import uuid4
import asyncio

from integration.python_api.cache import CacheDecorator, get_cache_client


def _dispatch_background_event(dispatcher, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(dispatcher(payload))


class ProjectTelemetryStore:
    def __init__(
        self,
        data_dir: Path,
        event_repository=None,
        feedback_repository=None,
        stats_repository=None,
        cache_client=None
    ) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.data_dir / "project_events.jsonl"
        self.stats_file = self.data_dir / "project_stats.json"
        self.feedback_file = self.data_dir / "draft_feedback.jsonl"
        self._lock = Lock()

        # Use repositories if provided, otherwise fall back to legacy file-based approach
        self.event_repository = event_repository
        self.feedback_repository = feedback_repository
        self.stats_repository = stats_repository
        self.cache_client = cache_client or get_cache_client()

        # Initialize cache decorators
        self._cache_decorator = CacheDecorator(self.cache_client, ttl=300)  # 5 minutes default

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        if self.event_repository is not None or self.feedback_repository is not None:
            raise RuntimeError("Using repositories but called legacy _append_jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _write_json_atomic(self, path: Path, payload: dict) -> None:
        if self.stats_repository is not None:
            raise RuntimeError("Using repositories but called legacy _write_json_atomic")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_name(f"{path.stem}.{uuid4().hex}.tmp")
        temp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(path)

    def record_event(self, payload: dict, source: str, result_path: str | None = None) -> None:
        from datetime import datetime
        from integration.python_api.repositories import ProjectEvent

        event = ProjectEvent(
            id=0,  # Will be set by repository
            code=str(payload.get("code", "")),
            company=str(payload.get("company", "")),
            part_name=str(payload.get("part_name", "")),
            diameter=float(payload.get("diameter", 0) or 0),
            length=float(payload.get("length", 0) or 0),
            source=source,
            result_path=result_path or "",
            created_at=datetime.utcnow(),
        )

        if self.event_repository is not None:
            self.event_repository.record_event(event)
        else:
            # Legacy implementation
            event_dict = {
                "code": str(payload.get("code", "")),
                "company": str(payload.get("company", "")),
                "part_name": str(payload.get("part_name", "")),
                "diameter": float(payload.get("diameter", 0) or 0),
                "length": float(payload.get("length", 0) or 0),
                "source": source,
                "result_path": result_path or "",
            }
            self._append_jsonl(self.events_file, event_dict)

        # Invalidate cache for stats, recommendations, templates, and drafts
        self.cache_client.clear_pattern("telemetry:*")

        # Send SSE event for real-time updates
        try:
            # Import here to avoid circular imports
            from server import send_telemetry_event
            event_data = {
                "timestamp": event.created_at.isoformat(),
                "event_type": "project_created",
                "data": {
                    "code": event.code,
                    "company": event.company,
                    "part_name": event.part_name,
                    "diameter": event.diameter,
                    "length": event.length,
                    "source": event.source,
                    "result_path": event.result_path
                },
                "type": "telemetry_event"
            }
            # Only schedule SSE updates when running inside an active event loop.
            _dispatch_background_event(send_telemetry_event, event_data)
        except Exception:
            # SSE bridge is optional for the API runtime.
            pass

    def rebuild_stats(self) -> dict:
        if self.event_repository is not None and self.feedback_repository is not None and self.stats_repository is not None:
            events = self.event_repository.get_all_events()
            feedback = self.feedback_repository.get_all_feedback()
            stats = self.stats_repository.rebuild_stats(events, feedback)
            return {
                "total_projects": stats.total_projects,
                "seed_projects": stats.seed_projects,
                "real_projects": stats.real_projects,
                "top_part_names": stats.top_part_names,
                "top_companies": stats.top_companies,
                "diameter_range": list(stats.diameter_range),
                "length_range": list(stats.length_range),
                "draft_feedback": {
                    "accepted": stats.draft_feedback_accepted,
                    "rejected": stats.draft_feedback_rejected,
                },
            }
        else:
            # Legacy implementation
            part_names: Counter[str] = Counter()
            companies: Counter[str] = Counter()
            diameters: list[float] = []
            lengths: list[float] = []
            count = 0
            seed_count = 0
            real_count = 0

            if self.events_file.exists():
                for line in self.events_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    count += 1
                    source = str(item.get("source", ""))
                    if source.startswith("seed."):
                        seed_count += 1
                    else:
                        real_count += 1
                    part_names[str(item.get("part_name", ""))] += 1
                    companies[str(item.get("company", ""))] += 1
                    diameters.append(float(item.get("diameter", 0) or 0))
                    lengths.append(float(item.get("length", 0) or 0))

            accepted_feedback = 0
            rejected_feedback = 0
            if self.feedback_file.exists():
                for line in self.feedback_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    feedback = str(item.get("feedback", ""))
                    if feedback == "accepted":
                        accepted_feedback += 1
                    elif feedback == "rejected":
                        rejected_feedback += 1

            stats = {
                "total_projects": count,
                "seed_projects": seed_count,
                "real_projects": real_count,
                "top_part_names": part_names.most_common(10),
                "top_companies": companies.most_common(10),
                "diameter_range": [min(diameters) if diameters else 0, max(diameters) if diameters else 0],
                "length_range": [min(lengths) if lengths else 0, max(lengths) if lengths else 0],
                "draft_feedback": {
                    "accepted": accepted_feedback,
                    "rejected": rejected_feedback,
                },
            }
            self._write_json_atomic(self.stats_file, stats)
            return stats

    def get_stats(self) -> dict:
        cache_key = "telemetry:stats"
        cached = self.cache_client.get(cache_key)
        if cached:
            return cached

        if self.stats_repository is not None:
            stats = self.stats_repository.get_stats()
            result = {
                "total_projects": stats.total_projects,
                "seed_projects": stats.seed_projects,
                "real_projects": stats.real_projects,
                "top_part_names": stats.top_part_names,
                "top_companies": stats.top_companies,
                "diameter_range": list(stats.diameter_range),
                "length_range": list(stats.length_range),
                "draft_feedback": {
                    "accepted": stats.draft_feedback_accepted,
                    "rejected": stats.draft_feedback_rejected,
                },
            }
        else:
            # Legacy implementation
            if not self.stats_file.exists():
                result = self.rebuild_stats()
            else:
                result = json.loads(self.stats_file.read_text(encoding="utf-8"))

        self.cache_client.set(cache_key, result, 300)  # Cache por 5 minutos
        return result

    def get_recommendations(self) -> dict:
        cache_key = "telemetry:recommendations"
        cached = self.cache_client.get(cache_key)
        if cached:
            return cached

        stats = self.get_stats()
        top_parts = stats.get("top_part_names", [])
        top_companies = stats.get("top_companies", [])
        diameter_range = stats.get("diameter_range", [0, 0])
        length_range = stats.get("length_range", [0, 0])
        result = {
            "suggested_part_name": top_parts[0][0] if top_parts else "Tubo",
            "suggested_company": top_companies[0][0] if top_companies else "",
            "typical_diameter_min": diameter_range[0],
            "typical_diameter_max": diameter_range[1],
            "typical_length_min": length_range[0],
            "typical_length_max": length_range[1],
            "total_projects": stats.get("total_projects", 0),
        }

        self.cache_client.set(cache_key, result, 300)  # Cache por 5 minutos
        return result

    def get_templates(self, limit: int = 5) -> list[dict]:
        cache_key = f"telemetry:templates:{limit}"
        cached = self.cache_client.get(cache_key)
        if cached:
            return cached

        # ... existing logic ...
        if self.event_repository is not None and self.feedback_repository is not None:
            events = self.event_repository.get_all_events()
            feedback = self.feedback_repository.get_all_feedback()
        else:
            # Legacy implementation - need to read from files
            events = []
            if self.events_file.exists():
                for line in self.events_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    from datetime import datetime
                    from integration.python_api.repositories import ProjectEvent
                    events.append(ProjectEvent(
                        id=len(events) + 1,
                        code=str(item.get("code", "")),
                        company=str(item.get("company", "")),
                        part_name=str(item.get("part_name", "")),
                        diameter=float(item.get("diameter", 0) or 0),
                        length=float(item.get("length", 0) or 0),
                        source=str(item.get("source", "")),
                        result_path=str(item.get("result_path", "")),
                        created_at=datetime.fromisoformat(item.get("created_at", datetime.utcnow().isoformat())),
                    ))

            feedback = []
            if self.feedback_file.exists():
                for line in self.feedback_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    from datetime import datetime
                    from integration.python_api.repositories import DraftFeedback
                    feedback.append(DraftFeedback(
                        id=len(feedback) + 1,
                        prompt=str(item.get("prompt", "")),
                        feedback=str(item.get("feedback", "")),
                        company=str(item.get("company", "")),
                        part_name=str(item.get("part_name", "")),
                        code=str(item.get("code", "")),
                        created_at=datetime.fromisoformat(item.get("created_at", datetime.utcnow().isoformat())),
                    ))

        grouped: dict[tuple[str, str], dict[str, object]] = defaultdict(
            lambda: {"count": 0, "diameters": [], "lengths": [], "score": 0}
        )
        for event in events:
            key = (event.company, event.part_name)
            if not key[0] or not key[1]:
                continue
            bucket = grouped[key]
            bucket["count"] = int(bucket["count"]) + 1
            bucket["diameters"].append(event.diameter)
            bucket["lengths"].append(event.length)

        for fb in feedback:
            key = (fb.company, fb.part_name)
            if key not in grouped:
                continue
            if fb.feedback == "accepted":
                grouped[key]["score"] = int(grouped[key]["score"]) + 3
            elif fb.feedback == "rejected":
                grouped[key]["score"] = int(grouped[key]["score"]) - 2

        ranked = sorted(
            grouped.items(),
            key=lambda kv: (int(kv[1]["score"]), int(kv[1]["count"])),
            reverse=True,
        )[:limit]
        templates = []
        for index, ((company, part_name), values) in enumerate(ranked, start=1):
            diameters = [value for value in values["diameters"] if value > 0]
            lengths = [value for value in values["lengths"] if value > 0]
            templates.append(
                {
                    "id": f"template-{index}",
                    "company": company,
                    "part_name": part_name,
                    "diameter": round(sum(diameters) / len(diameters), 2) if diameters else 120,
                    "length": round(sum(lengths) / len(lengths), 2) if lengths else 300,
                    "count": int(values["count"]),
                    "score": int(values["score"]),
                }
            )

        self.cache_client.set(cache_key, templates, 300)  # Cache por 5 minutos
        return templates

    def build_project_draft(
        self,
        company: str | None = None,
        part_name: str | None = None,
    ) -> dict:
        cache_key = f"telemetry:draft:{company or ''}:{part_name or ''}"
        cached = self.cache_client.get(cache_key)
        if cached:
            return cached

        templates = self.get_templates(limit=20)
        normalized_company = str(company or "").strip().lower()
        normalized_part_name = str(part_name or "").strip().lower()

        selected = None
        for template in templates:
            template_company = str(template.get("company", "")).strip().lower()
            template_part_name = str(template.get("part_name", "")).strip().lower()
            company_matches = not normalized_company or template_company == normalized_company
            part_matches = not normalized_part_name or template_part_name == normalized_part_name
            if company_matches and part_matches:
                selected = template
                break

        if not selected and templates:
            selected = templates[0]

        recommendations = self.get_recommendations()
        base_company = selected["company"] if selected else recommendations["suggested_company"]
        base_part_name = selected["part_name"] if selected else recommendations["suggested_part_name"]
        base_diameter = selected["diameter"] if selected else recommendations["typical_diameter_max"] or 120
        base_length = selected["length"] if selected else recommendations["typical_length_max"] or 300

        safe_company = base_company or company or "Empresa Modelo"
        safe_part = base_part_name or part_name or "Tubo"
        code_prefix = "".join(ch for ch in safe_part.upper() if ch.isalnum())[:4] or "AUTO"

        result = {
            "company": safe_company,
            "part_name": safe_part,
            "diameter": float(base_diameter),
            "length": float(base_length),
            "code": f"{code_prefix}-{recommendations['total_projects'] + 1:04d}",
            "based_on_template": selected["id"] if selected else None,
            "confidence": "high" if selected else "medium",
        }

        self.cache_client.set(cache_key, result, 600)  # Cache por 10 minutos para drafts
        return result

    def build_project_draft_from_text(self, prompt: str) -> dict:
        parsed = self._extract_prompt_hints(prompt)
        draft = self.build_project_draft(
            company=parsed.get("company"),
            part_name=parsed.get("part_name"),
        )
        if parsed.get("diameter") is not None:
            draft["diameter"] = float(parsed["diameter"])
        if parsed.get("length") is not None:
            draft["length"] = float(parsed["length"])
        draft["parsed_fields"] = [key for key, value in parsed.items() if value not in (None, "")]
        draft["prompt"] = prompt
        draft["confidence"] = "high" if len(draft["parsed_fields"]) >= 3 else "medium"
        draft["field_confidence"] = {
            "company": "high" if parsed.get("company") else "medium",
            "part_name": "high" if parsed.get("part_name") else "medium",
            "diameter": "high" if parsed.get("diameter") is not None else "medium",
            "length": "high" if parsed.get("length") is not None else "medium",
            "code": "medium",
        }
        draft["explanation"] = (
            "Rascunho montado a partir do texto informado e completado com historico do sistema."
        )
        return draft

    def record_draft_feedback(self, prompt: str, draft: dict, feedback: str) -> None:
        from datetime import datetime
        from integration.python_api.repositories import DraftFeedback

        feedback_obj = DraftFeedback(
            id=0,  # Will be set by repository
            prompt=str(prompt or ""),
            feedback=str(feedback or ""),
            company=str(draft.get("company", "")),
            part_name=str(draft.get("part_name", "")),
            code=str(draft.get("code", "")),
            ai_response=None,
            tokens_used=None,
            created_at=datetime.utcnow(),
        )

        if self.feedback_repository is not None:
            self.feedback_repository.record_feedback(feedback_obj)
        else:
            # Legacy implementation
            item = {
                "prompt": str(prompt or ""),
                "feedback": str(feedback or ""),
                "company": str(draft.get("company", "")),
                "part_name": str(draft.get("part_name", "")),
                "code": str(draft.get("code", "")),
            }
            self._append_jsonl(self.feedback_file, item)

        # Keep insights consistent right after feedback submission.
        self.rebuild_stats()

        # Invalidate cache for stats, recommendations, templates, and drafts
        self.cache_client.clear_pattern("telemetry:*")

        # Send SSE event for real-time updates
        try:
            from server import send_telemetry_event
            feedback_data = {
                "timestamp": feedback_obj.created_at.isoformat(),
                "event_type": "feedback_recorded",
                "data": {
                    "feedback": feedback_obj.feedback,
                    "company": feedback_obj.company,
                    "part_name": feedback_obj.part_name,
                    "code": feedback_obj.code,
                    "prompt": feedback_obj.prompt
                },
                "type": "feedback_event"
            }
            _dispatch_background_event(send_telemetry_event, feedback_data)
        except Exception:
            pass

    def _extract_prompt_hints(self, prompt: str) -> dict:
        text = str(prompt or "").strip()
        lowered = text.lower()
        hints = {
            "company": None,
            "part_name": None,
            "diameter": None,
            "length": None,
        }

        part_aliases = {
            "tubo": "Tubo",
            "curva": "Curva",
            "tee": "Tee",
            "flange": "Flange",
            "reducer": "Reducer",
            "valve": "Valve",
            "valvula": "Valve",
            "válvula": "Valve",
        }
        for alias, normalized in part_aliases.items():
            if alias in lowered:
                hints["part_name"] = normalized
                break

        company_match = re.search(r"\bpara\s+([a-z0-9][a-z0-9\s_-]{1,80})", lowered, re.IGNORECASE)
        if company_match:
            raw_company = company_match.group(1).strip(" .,-")
            hints["company"] = " ".join(word.capitalize() for word in raw_company.split())

        diameter_match = re.search(r"(?:diametro|diâmetro|diameter|d)\s*(?:de|=)?\s*(\d+(?:[.,]\d+)?)", lowered, re.IGNORECASE)
        if diameter_match:
            hints["diameter"] = float(diameter_match.group(1).replace(",", "."))
        else:
            mm_match = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", lowered, re.IGNORECASE)
            if mm_match:
                hints["diameter"] = float(mm_match.group(1).replace(",", "."))

        length_match = re.search(r"(?:comprimento|length|c)\s*(?:de|=)?\s*(\d+(?:[.,]\d+)?)", lowered, re.IGNORECASE)
        if length_match:
            hints["length"] = float(length_match.group(1).replace(",", "."))

        return hints
