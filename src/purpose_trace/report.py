"""Portable reports with no scripts, remote resources, or raw context values."""

from html import escape

from .util import canonical


def html_report(report: dict) -> str:
    e = lambda value: escape(str(value), quote=True)
    rows = []
    for result in report["results"]:
        witness = result.get("witness", {})
        detail = ", ".join(witness.get("changed_paths", []))
        if "p_value" in result:
            detail = f"TV={result['max_total_variation']} · p={result['p_value']} · α={result['corrected_alpha']:.6g}"
        rows.append(f"<tr><td>{e(result['cohort'])}<small>{e(result['group'][:16])}</small></td>"
                    f"<td>{e(result['status'])}</td><td>{result['contexts']}</td>"
                    f"<td>{result['samples']}</td><td>{e(result['reason'])}<small>{e(detail)}</small></td></tr>")
    limitations = "".join(f"<li>{e(item)}</li>" for item in report["limitations"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PurposeTrace · {e(report['status'])}</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1120px;margin:48px auto;padding:0 24px;color:#142d35;background:#f7faf8}}h1{{font-size:44px;line-height:1.1}}.label{{letter-spacing:.12em;text-transform:uppercase;color:#466d65}}.status{{font-size:24px;font-weight:700}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:left;padding:16px;border-bottom:1px solid #d6e1dd}}small{{display:block;color:#52696b;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0ed;padding:24px;font-size:12px}}code{{overflow-wrap:anywhere}}@media print{{body{{margin:0}}details{{display:block}}}}</style></head>
<body><p class="label">PurposeTrace / audit evidence</p><h1>Does private context change what leaves?</h1>
<p class="status">{e(report['status'])}</p><p>{report['records']} records · {report['groups']} comparison groups · {e(report['policy']['mode'])}</p>
<p>Policy: <strong>{e(report['policy']['name'])}</strong><br><small>{e(report['policy']['fingerprint'])}</small></p>
<p>Generated {e(report['created_at'])}. Evidence digest: <code>{e(report['evidence_digest'])}</code></p>
<div class="scroll"><table><thead><tr><th>Cohort / group</th><th>Result</th><th>Contexts</th><th>Samples</th><th>Evidence</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Interpretation boundaries</h2><ul>{limitations}</ul>
<details><summary>Complete machine-readable evidence</summary><pre>{e(canonical(report))}</pre></details>
<p>PurposeTrace 1.0.0 · Local analysis · No external requests</p></body></html>"""
