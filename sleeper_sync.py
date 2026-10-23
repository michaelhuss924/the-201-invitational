#!/usr/bin/env python3
"""The 201 Invitational: sync public Sleeper NFL league into website-importable JSON.

Run: python3 sleeper_sync.py
Then open index.html > Sleeper hub > Import snapshot JSON.
No login or third-party dependencies. Internet required when this script runs.
"""
import argparse
import datetime
import json
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_LEAGUE = '1352473165539864576'
BASE = 'https://api.sleeper.app/v1'


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={'User-Agent': 'The201Invitational/1.0 (noncommercial league site)'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def team_name(roster, users_by_id):
    u = users_by_id.get(str(roster.get('owner_id')), {})
    return (u.get('metadata') or {}).get('team_name') or (roster.get('metadata') or {}).get('team_name') or u.get('display_name') or f"Roster {roster['roster_id']}"


def normalize(values, n):
    low, high = min(values), max(values)
    return 0.5 if high == low else (n-low)/(high-low)


def build_snapshot(league, users, rosters, nfl_state, weeks, upcoming, traded_picks):
    users_by_id = {str(u.get('user_id')): u for u in users}
    summaries = []
    for roster in rosters:
        rid = roster['roster_id']
        settings = roster.get('settings') or {}
        games = []
        for week in sorted(weeks):
            m = next((x for x in (weeks[week] or []) if x['roster_id'] == rid), None)
            if m and isinstance(m.get('points'), (float,int)):
                pts = m['custom_points'] if m.get('custom_points') is not None else m['points']
                games.append({'week':week,'points':float(pts),'matchup':m.get('matchup_id')})
        pts = sum(g['points'] for g in games)
        recent = games[-3:]
        wins, losses, ties = [int(settings.get(k) or 0) for k in ('wins','losses','ties')]
        summary = dict(rosterId=rid,userId=str(roster.get('owner_id') or ''),name=team_name(roster, users_by_id),owner=users_by_id.get(str(roster.get('owner_id')),{}).get('display_name',''),
                       wins=wins,losses=losses,ties=ties,
                       pf=float(settings.get('fpts') or 0)+float(settings.get('fpts_decimal') or 0)/100 or pts,
                       pa=float(settings.get('fpts_against') or 0)+float(settings.get('fpts_against_decimal') or 0)/100,
                       ppg=pts/len(games) if games else 0.,
                       recentPpg=sum(x['points'] for x in recent)/len(recent) if recent else 0.,
                       games=games,players=roster.get('players') or [],starters=roster.get('starters') or [],
                       taxi=roster.get('taxi') or [],reserve=roster.get('reserve') or [],
                       record=f'{wins}-{losses}' + (f'-{ties}' if ties else ''),
                       winPct=(wins+0.5*ties)/(wins+losses+ties) if wins+losses+ties else 0.)
        summaries.append(summary)
    for t in summaries:
        all_wins, all_games = 0., 0
        for g in t['games']:
            for opp in summaries:
                if t is opp: continue
                other = next((x for x in opp['games'] if x['week']==g['week']),None)
                if other:
                    all_games += 1
                    all_wins += 1 if g['points']>other['points'] else (0.5 if g['points']==other['points'] else 0)
        t['allPlayWins']=all_wins
        t['allPlayGames']=all_games
        t['allPlayPct']=all_wins/all_games if all_games else 0.
    for t in summaries:
        weights = {'ppg':0.4,'allPlayPct':0.25,'recentPpg':0.2,'winPct':0.15}
        t['powerScore']=round(100*sum(weight*normalize([x[key] for x in summaries],t[key]) for key,weight in weights.items()),1)
        t['trendPpg']=round(t['recentPpg']-t['ppg'],1)
    summaries.sort(key=lambda x:(-x['powerScore'],-x['ppg']))
    pairings={}
    for m in upcoming or []:
        if m.get('matchup_id') is not None:
            pairings.setdefault(str(m['matchup_id']),[]).append(m)
    by_roster={t['rosterId']:t for t in summaries}
    next_matchups=[]
    for match_id, pair in pairings.items():
        if len(pair)!=2: continue
        a,b=by_roster.get(pair[0]['roster_id']),by_roster.get(pair[1]['roster_id'])
        if not a or not b: continue
        next_matchups.append(dict(matchupId=match_id,teamA=a['name'],teamB=b['name'],aId=a['rosterId'],bId=b['rosterId'],combinedScore=round(a['powerScore']+b['powerScore'],1)))
    next_matchups.sort(key=lambda x:-x['combinedScore'])
    last=max(weeks.keys()) if weeks else 0
    return {'leagueId':str(league['league_id']), 'leagueName':league.get('name','The 201 Invitational'), 'season':int(league['season']),
            'status':league.get('status'), 'syncedAt':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),
            'lastCompletedWeek':last, 'nextWeek':last+1, 'teamCount':len(rosters),
            'settings':league.get('settings') or {},'scoring':league.get('scoring_settings') or {},'rosterPositions':league.get('roster_positions') or [],
            'previousLeagueId':league.get('previous_league_id'), 'standings':summaries,'nextMatchups':next_matchups,
            'tradedPicks':traded_picks or [],'source':'Sleeper public API',
            'method':'Power score = 40% season PPG + 25% all-play wins + 20% last-three PPG + 15% official winning percentage. Each metric normalized against the current league.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league-id', default=DEFAULT_LEAGUE)
    parser.add_argument('--through-week',type=int,help='Override final completed week (default: NFL current week minus one)')
    parser.add_argument('--output',default='sleeper_snapshot_2026.json')
    args=parser.parse_args()
    lid=args.league_id.strip().split('/')[-1]
    if not lid.isdigit(): parser.error('League ID must be numeric')
    print('Reading Sleeper league settings, team owners, and rosters…')
    league=fetch(f'/league/{lid}')
    if not league: raise RuntimeError('League ID not found')
    users=fetch(f'/league/{lid}/users');rosters=fetch(f'/league/{lid}/rosters');nfl=fetch('/state/nfl')
    if args.through_week is not None: last=args.through_week
    elif str(nfl.get('season'))==str(league.get('season')): last=max(0,int(nfl.get('week') or 1)-1)
    elif league.get('status')=='complete': last=18
    else: last=0
    last=max(0,min(last,18))
    print(f"Verified league: {league.get('name')} ({league.get('season')}); {len(rosters)} rosters; collecting through Week {last}.")
    weeks={w:fetch(f'/league/{lid}/matchups/{w}') for w in range(1,last+1)}
    try: upcoming=fetch(f'/league/{lid}/matchups/{min(last+1,18)}')
    except (urllib.error.HTTPError,urllib.error.URLError): upcoming=[]
    try: traded_picks=fetch(f'/league/{lid}/traded_picks')
    except (urllib.error.HTTPError,urllib.error.URLError): traded_picks=[]
    snapshot=build_snapshot(league, users, rosters, nfl, weeks, upcoming, traded_picks)
    out=Path(args.output)
    out.write_text(json.dumps(snapshot,indent=2),encoding='utf8')
    print(f"Created {out.resolve()} — {len(snapshot['standings'])} teams, {snapshot['lastCompletedWeek']} finished weeks.\nOpen website > Sleeper hub > Import snapshot JSON.")

if __name__=='__main__':main()
