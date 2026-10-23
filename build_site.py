#!/usr/bin/env python3
"""Embed a verified Sleeper league snapshot into The 201 Invitational static site.

Runs only after sleeper_sync.py (local or via the included GitHub Action).
No AI-generated opinions, fictional scores, or speculative narratives are published.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEAGUE_ID = '1352473165539864576'
SCRIPT_RE = re.compile(r'(<script id="site-data" type="application/json">)(.*?)(</script>)', re.S)


def load_embedded(html: str) -> dict:
    match = SCRIPT_RE.search(html)
    if match is None:
        raise ValueError('Website is missing site-data element')
    return json.loads(match.group(2))


def final_results(snapshot: dict) -> list:
    """Read scores for the last completed week without inventing a game result."""
    last = int(snapshot.get('lastCompletedWeek') or 0)
    if last < 1:
        return []
    matchups = {}
    for t in snapshot['standings']:
        week = next((g for g in t.get('games', []) if int(g['week']) == last), None)
        if not week or week.get('matchup') is None or not isinstance(week.get('points'), (float, int)):
            continue
        key = str(week['matchup'])
        matchups.setdefault(key, []).append((t, float(week['points'])))
    rows = []
    for match_id, sides in matchups.items():
        if len(sides) != 2:
            continue
        (a, points_a), (b, points_b) = sorted(sides, key=lambda x: int(x[0]['rosterId']))
        rows.append(dict(matchupId=match_id, teamA=a['name'], aId=a['rosterId'],
                         teamB=b['name'], bId=b['rosterId'], pointsA=round(points_a, 2),
                         pointsB=round(points_b, 2)))
    # Sort closest contests first, keeps the weekly highlight script engaging.
    rows.sort(key=lambda r: (abs(r['pointsA'] - r['pointsB']), str(r['matchupId'])))
    return rows


def sync_content(base: dict, snapshot: dict, previous: dict | None) -> dict:
    league_id = str(snapshot.get('leagueId'))
    if league_id != LEAGUE_ID or not isinstance(snapshot.get('scoring'), dict):
        raise ValueError('Unexpected Sleeper league or scoring structure; not publishing')
    if not isinstance(snapshot.get('standings'), list) or not snapshot['standings']:
        raise ValueError('No verified teams returned; not publishing')
    updated = copy.deepcopy(base)
    snapshot = copy.deepcopy(snapshot)
    snapshot['lastResults'] = final_results(snapshot)
    updated['sleeper'] = snapshot
    updated['teams'] = [dict(name=t['name'], owner=t.get('owner', ''), rosterId=t['rosterId'], userId=t.get('userId', '')) for t in snapshot['standings']]
    old_entries = ((previous or {}).get('rankings') or {}).get('season2026', {}).get('entries', [])
    previous_positions = {e['team']: i + 1 for i, e in enumerate(old_entries)}
    rankings = []
    for i, t in enumerate(snapshot['standings']):
        old = previous_positions.get(t['name'])
        trend = 'New' if old is None else 'Up' if old > i + 1 else 'Down' if old < i + 1 else 'Same'
        rankings.append(dict(id='sleeper-' + str(t['rosterId']), team=t['name'],
                             record=t.get('record', ''), trend=trend,
                             blurb=f"Power score {t['powerScore']} / 100. {t['ppg']:.1f} PPG; "
                                   f"{round(100*t['allPlayPct'])}% all-play rate; "
                                   f"{t['recentPpg']:.1f} PPG over last three weeks."))
    updated.setdefault('rankings', {})['season2026'] = dict(
        updated=str(snapshot['syncedAt'])[:10],
        intro=f"Objective performance index through Week {snapshot['lastCompletedWeek']}. {snapshot['method']}",
        entries=rankings,
    )
    # Preserve the previously published lineup of editorial articles, sprites,
    # owner mappings and archival info only from the hand-maintained site-content.json.
    # We deliberately do NOT fabricate or silently publish AI-written articles here.
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', help='JSON produced by sleeper_sync.py. Omit to render base site without live scores.')
    args = parser.parse_args()
    template = (ROOT / 'site-template.html').read_text(encoding='utf-8')
    data = json.loads((ROOT / 'site-content.json').read_text(encoding='utf-8'))
    published = ROOT / 'public' / 'index.html'
    previous = load_embedded(published.read_text('utf-8')) if published.is_file() else None
    if args.snapshot:
        snapshot = json.loads(Path(args.snapshot).read_text('utf-8'))
        data = sync_content(data, snapshot, previous)
        print(f"Synced {len(data['teams'])} teams and {len(data['sleeper']['lastResults'])} completed matchups from Week {data['sleeper']['lastCompletedWeek']}.")
    content = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    replacement = lambda m: m.group(1) + content + m.group(3)
    if len(SCRIPT_RE.findall(template)) != 1:
        raise ValueError('Expected one site-data script in template')
    rendered = SCRIPT_RE.sub(replacement, template, count=1)
    # Roundtrip parse to catch malformed injected JSON before releasing it.
    assert load_embedded(rendered)['settings']['name'] == data['settings']['name']
    published.parent.mkdir(parents=True, exist_ok=True)
    published.write_text(rendered, encoding='utf-8')
    print('Updated', published)


if __name__ == '__main__':
    main()
