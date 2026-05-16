#!/usr/bin/env python3
"""Convert investment brief to PDF using reportlab."""

import sys
sys.path.insert(0, '/opt/homebrew/lib/python3.14/site-packages')

import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics

# ── Color palette ──────────────────────────────────────────────────────────
NAVY   = colors.HexColor('#0d1b4b')
GOLD   = colors.HexColor('#f0a500')
BLUE   = colors.HexColor('#1a3a6e')
LIGHT  = colors.HexColor('#f7f9fc')
BORDER = colors.HexColor('#e0e0e0')
WHITE  = colors.white
GRAY   = colors.HexColor('#555555')
LINK   = colors.HexColor('#1a6bb5')

# ── Styles ─────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

styles = {
    'h1':    S('h1',    fontName='Helvetica-Bold', fontSize=20, textColor=NAVY,
                        spaceAfter=2, leading=24, borderPadding=(0,0,4,0)),
    'h2':    S('h2',    fontName='Helvetica-Bold', fontSize=13, textColor=NAVY,
                        spaceBefore=14, spaceAfter=3, leading=16),
    'h3':    S('h3',    fontName='Helvetica-Bold', fontSize=11, textColor=BLUE,
                        spaceBefore=10, spaceAfter=2, leading=14),
    'h4':    S('h4',    fontName='Helvetica-Bold', fontSize=9.5, textColor=BLUE,
                        spaceBefore=6, spaceAfter=1, leading=12),
    'body':  S('body',  fontName='Helvetica',      fontSize=8.5, textColor=colors.black,
                        spaceAfter=3, leading=12),
    'bold':  S('bold',  fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.black,
                        spaceAfter=3, leading=12),
    'meta':  S('meta',  fontName='Helvetica',      fontSize=7.5, textColor=GRAY,
                        spaceAfter=2, leading=10),
    'li':    S('li',    fontName='Helvetica',      fontSize=8.5, textColor=colors.black,
                        spaceAfter=2, leading=12, leftIndent=14, bulletIndent=4),
}

TH_STYLE = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=7.5,
                           textColor=WHITE, leading=10)
TD_STYLE = ParagraphStyle('td', fontName='Helvetica', fontSize=7.5,
                           textColor=colors.black, leading=10)

def para(text, style='body'):
    """Render inline markdown (bold, italic) inside a Paragraph."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.*?)\*\*',     r'<b>\1</b>',         text)
    text = re.sub(r'\*(.*?)\*',         r'<i>\1</i>',         text)
    text = re.sub(r'`(.*?)`',           r'<font name="Courier" size="7">\1</font>', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'<u>\1</u>', text)
    return Paragraph(text, styles[style])

def make_table(rows, col_widths=None, has_header=True):
    """Build a styled Table from a list of row-lists (strings)."""
    page_w = A4[0] - 3.6*cm
    if col_widths is None:
        ncols = max(len(r) for r in rows)
        col_widths = [page_w / ncols] * ncols

    data = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, cell in enumerate(row):
            style = TH_STYLE if (has_header and ri == 0) else TD_STYLE
            cells.append(Paragraph(str(cell), style))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1 if has_header else 0)

    cmd = [
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 7.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT]),
        ('GRID',       (0,0), (-1,-1), 0.4, BORDER),
        ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',(0,0), (-1,-1), 5),
        ('RIGHTPADDING',(0,0),(-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1), 3),
    ]
    t.setStyle(TableStyle(cmd))
    return t

def section_rule():
    return HRFlowable(width='100%', thickness=1.5, color=GOLD, spaceAfter=4)

def light_rule():
    return HRFlowable(width='100%', thickness=0.5, color=BORDER, spaceAfter=3)

# ══════════════════════════════════════════════════════════════════════════
# DOCUMENT CONTENT
# ══════════════════════════════════════════════════════════════════════════
story = []

# ── Title ──────────────────────────────────────────────────────────────────
story.append(para('Investment Brief — March 5, 2026', 'h1'))
story.append(section_rule())
story.append(para('<b>Coverage Period</b>: February 26 – March 5, 2026', 'meta'))
story.append(Spacer(1, 6))

# ── Market Snapshot ────────────────────────────────────────────────────────
story.append(para('Market Snapshot', 'h2'))
story.append(light_rule())

mkt_rows = [
    ['Market', 'Level', '7D Change', 'Trend'],
    ['BTC',          '$72,000', '+6.23%',    'Up (recovery rally)'],
    ['ETH',          '$2,119',  '~+2.5%',    'Up'],
    ['Crypto Mkt Cap','$2.48T', '+3.1%',     'Up'],
    ['BTC Dominance','57.1%',   '—',         'Flat'],
    ['S&P 500',      '~6,850',  'Negative',  'Down (volatile)'],
    ['NASDAQ',       '~22,828', 'Negative',  'Down'],
    ['DXY',          '~99.07',  '+0.70%',    'Rebounding'],
    ['10Y Yield',    '4.14%',   '+4 sessions','Up'],
    ['Brent Crude',  '~$80-82', '+10-13%',   'Up (geopolitical spike)'],
    ['Fear & Greed', '22',      '—',         'Extreme Fear'],
]
story.append(make_table(mkt_rows, col_widths=[3.2*cm, 2.6*cm, 3*cm, 6.5*cm]))
story.append(Spacer(1, 4))

story.append(para('<b>Key macro developments</b>: U.S./Israeli strikes on Iran killed the Iranian supreme leader, triggering an oil shock with Brent crude surging 10-13% and embedding a geopolitical risk premium. The inflation risk is forcing the Fed into a hawkish hold — markets now pricing just <b>one 25bps cut in all of 2026</b>, down from two expected earlier this week.'))
story.append(Spacer(1, 4))
story.append(para('<b>Upcoming catalysts</b>:', 'bold'))
for item in [
    'FOMC Meeting: March 17-18, 2026 (rate decision + Powell press conference; consensus = hold)',
    'CPI (February 2026 data): Expected week of March 9-12 — critical given oil-driven inflation fears',
    'NFP: March 6, 2026 (tomorrow)',
    'BTC spot ETF flow data — 3-day inflow streak being watched closely for continuation',
    'Fed blackout period begins ~March 7-8; any speaker this week is elevated priority',
]:
    story.append(para(f'• {item}', 'li'))
story.append(Spacer(1, 6))

# ── Consensus Stance Table ─────────────────────────────────────────────────
story.append(para('Consensus Stance Table', 'h2'))
story.append(light_rule())
story.append(para('<i>Assets mentioned by 2+ traders only.</i>', 'meta'))
story.append(Spacer(1, 3))

cs_rows = [
    ['Asset', 'Bullish', 'Bearish', 'Neutral/Watching', 'Net'],
    ['BTC',
     'Myles G, PaikCapital, CavanXy, Pentoshi, Insomniac (cond.)',
     'Cowen, Loukas, TraderMayne (macro), Anbessa',
     'DonAlt, CredibleCrypto, Mercury (closed), ExitLiqNick, Follis',
     'Mixed — lower high debate'],
    ['ETH',
     'IncomeSharks (cautious), Mercury (rotation watch)',
     '—',
     'BattleRhino, CavanXy (flat)',
     'Neutral'],
    ['SOL',        'Bluntz, ColdBloodedShiller', '—', '—', 'Bullish (few)'],
    ['SPX/Equities','Fejau (Goldilocks)',
     'Quinn Thompson, Loukas, TraderMayne, CBS, Mercury, CryptoCondom, Smiley, CavanXy, Cowen',
     'IncomeSharks (ranging)',
     'Bearish consensus'],
    ['Gold/Metals', 'Quinn Thompson, ColdBloodedShiller', 'IncomeSharks (ST)', '—', 'Bullish'],
    ['Energy/Oil',  'Quinn Thompson (energy stocks)', 'Bluntz (fear pump)', 'Fejau (cautious)', 'Mixed'],
    ['Uranium',     'Bluntz, CryptoCondom', '—', '—', 'Bullish (high conviction)'],
    ['Commodities', 'Quinn Thompson, Insomniac, Citrini (offshore drilling)', '—', '—', 'Bullish'],
    ['Software/SaaS','—', 'Quinn Thompson, Fwd Guidance, Citrini (scenario)', '—', 'Bearish'],
    ['Bonds/Duration','—', 'Quinn Thompson, Forward Guidance', '—', 'Bearish'],
]
story.append(make_table(cs_rows, col_widths=[2.4*cm, 3.6*cm, 4*cm, 3.8*cm, 1.7*cm]))
story.append(Spacer(1, 4))

story.append(para('<b>Notable disagreements</b>:', 'bold'))
for d in [
    '<b>BTC lower high debate</b>: Benjamin Cowen called this rally weeks in advance as a predictable lower high (midterm year pattern: 2014, 2018, 2022 all peaked in week 1 of March). Myles G is calling the same rally the start of a bull run to $111K.',
    '<b>ExitLiqNick vs Myles G</b>: ExitLiqNick calls $72-85K a bull trap ("get people bullish at the .382 then dump"). Myles G calls $80K just the first stop to $98K+.',
    '<b>Oil</b>: Quinn Thompson long energy names (+20% since Dec) and adding on Iran catalyst. Bluntz calls the recent oil move a fear pump and does not believe the major annual bottom is in yet.',
]:
    story.append(para(f'• {d}', 'li'))
story.append(Spacer(1, 8))

# ── Tier 1 ─────────────────────────────────────────────────────────────────
story.append(para('Tier 1 — Deep Analysis (Substack Traders)', 'h2'))
story.append(section_rule())

# Citrini
story.append(KeepTogether([
    para('Citrini — @Citrini7', 'h3'),
    para('<b>Source</b>: No new Substack posts in window (most recent: "The 2028 Global Intelligence Crisis" — Feb 22) | X activity Feb 26–Mar 5'),
    para('<b>Key Thesis</b>: The 2028 GIC piece models a self-reinforcing AI displacement spiral where white-collar job destruction creates a deflationary feedback loop. Framed explicitly as a <i>scenario analysis, not a prediction or trade recommendation</i>. Citrini spent much of the week on X defending the piece against Citadel Securities and White House economists. Active positioning (26 Trades for 2026) is performing — 24/26 positive, up double the S&P YTD.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['S&P 500',         'Bearish (scenario)', 'Long-term', 'GIC scenario: ~57% peak-to-trough to ~3,500 via AI displacement + consumer spending collapse'],
    ['Software/SaaS',   'Bearish', 'Medium-long', 'Agentic AI makes custom coding cheaper than SaaS; recurring revenue assumptions break down'],
    ['Payments (MA/V/AXP)', 'Bearish', 'Medium-long', '"Friction going to zero" via AI agents eliminates intermediation revenue'],
    ['Offshore Drilling','Bullish', 'Medium', 'Up ~50% since Dec 2025; top performer in 26 Trades portfolio'],
    ['AI Materials (Nittobo, Resonac)', 'Bullish', 'Medium', 'Up 75% and 60% respectively since Dec 2025 publication'],
], col_widths=[3.2*cm, 2.8*cm, 2.4*cm, 7*cm]))
story.append(Spacer(1, 10))

# Quinn Thompson
story.append(KeepTogether([
    para('Quinn Thompson — @qthomp', 'h3'),
    para('<b>Sources</b>: "Scouting the Tape — Mar 1, 2026" | "Forward Guidance Chartbook — Feb 26, 2026"'),
    para('<b>Key Thesis</b>: Semiconductors have topped for a prolonged period; commodities (energy, natural gas, gold) are the superior risk-adjusted trade. Equities will grind lower rather than crash sharply due to existing hedge structures. The macro environment is defined by AI labor displacement anxiety, a Fed behind the curve, fiscal deterioration, and geopolitical energy supply disruption.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Semiconductors (SOX)', 'Bearish', 'Medium-long', '"Semis have topped for a very long time." Overcrowded; hyperscaler capex cuts incoming'],
    ['US Equities (SPX)', 'Bearish (slow bleed)', 'Short-medium', 'Slow frustrating grind lower; hedge structure limits velocity of decline'],
    ['Small Caps (IWM)', 'Bearish', 'Near-term', 'Long puts; cyclical narratives disconnected from fundamentals'],
    ['US Bonds/Duration', 'Bearish', 'Medium-long', 'Nominal yield differentials vs Japan/Europe at multi-year lows; 5.5-6% deficit projections'],
    ['Oil/Energy (XLE, USO, OIH, XES, IGE)', 'Bullish', 'Medium', 'Up +20% in under 2 months since Dec; Iran/Venezuela geopolitical support; energy is hottest CPI component'],
    ['Natural Gas (EQT, AR, RRC, CRK, CNX, EXE)', 'Bullish', 'Medium', '"Prices back in value territory"; QatarEnergy disruption from Iran attack; multiple upcoming catalysts'],
    ['Gold', 'Bullish', 'Medium-long', '"New risk-off safe haven" replacing bonds; Fed-Treasury coordination creates structural bid'],
], col_widths=[3.8*cm, 2.6*cm, 2.2*cm, 6.8*cm]))
story.append(para('<b>Active Trades</b>: Long energy (XLE, USO, OIH) + natural gas (EQT, AR, RRC) since December, up 20%. Long gold. Short SOX. Long IWM puts.', 'meta'))
story.append(Spacer(1, 10))

# Insomniac
story.append(KeepTogether([
    para('Insomniac — @insomniacxbt', 'h3'),
    para('<b>Sources</b>: "3.4.26 — the coins are back" (Mar 4) | "2.27.26 — uncertainty" (Feb 28)'),
    para('<b>Key Thesis</b>: AI uncertainty is creating valuation fog across individual tech names. The one trade that has been working and still does not feel consensus is commodities. On BTC: cautiously constructive contingent on $67-68K holding; if it holds, $80K is plausible.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Conditionally Bullish', 'Short-medium', '"$67-68K holds = good." Avoided heavy capitulation. Target: ~$80K'],
    ['BTC below $67-68K', 'Re-evaluate', '—', 'Stated pivot point — break changes thesis entirely'],
    ['Commodities', 'Bullish', 'Medium', '"The simple trade that actually doesn\'t feel consensus (yet) is still commodities."'],
    ['Individual Tech', 'Cautious', 'Short-term', 'AI uncertainty creates valuation fog; strongest performers "still look bleak"'],
    ['Crypto HTF', 'Bearish', 'Longer', '"HTF still looks ugly" — higher timeframe structure not repaired'],
], col_widths=[3.2*cm, 2.8*cm, 2.4*cm, 7*cm]))
story.append(Spacer(1, 10))

# ── Tier 2 ─────────────────────────────────────────────────────────────────
story.append(para('Tier 2 — Video & Social Commentary (YouTube + X)', 'h2'))
story.append(section_rule())

# Bob Loukas
story.append(KeepTogether([
    para('Bob Loukas — @BobLoukas', 'h3'),
    para('<b>Sources</b>: X tweets + bitcoin.live ("Reversal Potential in Play" Mar 4 | "Weekly Cycles Report" Mar 2)'),
    para('<b>Key Thesis</b>: Stocks flashing cyclical bear market signals at the 4-year cycle peak. BTC weekly chart "horrendous" and "hanging by a thread." Gold miners the standout. Market resolution is geopolitical-dependent.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Bearish (weekly) / Watching ST reversal', 'Medium bearish', 'Weekly chart "horrendous." Counter-trend rally potential being watched on Mar 4.'],
    ['Stocks', 'Bearish — cyclical bear signal', 'Medium', 'Cyclical bear triggered Mar 3. Day 31 of pressure on Jan 20 cycle low. Bollinger bands tightening. Resembles 2015 topping pattern.'],
    ['Gold Miners', 'Bullish', 'Medium', '"Showing nice resilience." Up 400% in 24 months.'],
], col_widths=[3*cm, 3.6*cm, 2.4*cm, 6.4*cm]))
story.append(para('<i>"As deeply oversold as Bitcoin is, this weekly chart remains horrendous and from a purely visual perspective, feels like it\'s hanging on by a thread and readying for another big leg lower."</i> — Mar 2', 'meta'))
story.append(Spacer(1, 8))

# TraderMayne
story.append(KeepTogether([
    para('TraderMayne — @Tradermayne', 'h3'),
    para('<b>Sources</b>: X tweets + Discord (#tm-charts, #crypto-trade-ideas-mayne, Feb 28–Mar 4)'),
    para('<b>Key Thesis</b>: Bought BTC at the lows, successfully traded the bounce to $70-72K, and largely exited (25% moon bag remaining). Views this as a lower high in a macro downtrend. Actively short S&P 500.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Macro Bearish / Traded the bounce', 'Closed longs; expecting lower high', '"Still believe we are in a macro downtrend, so the higher we go the better the next potential short opportunity is." Moon bag target $77K+.'],
    ['S&P 500', 'Bearish (actively short)', 'Short-term', 'Bears trying to break market structure. No FOMC rate cuts expected Mar 17-18.'],
], col_widths=[3*cm, 3.6*cm, 2.4*cm, 6.4*cm]))
story.append(para('<i>Discord (Mar 4)</i>: "Closing rest of longs up here. There\'s a world where this trades to ~$77k+. We sniped the bottom."', 'meta'))
story.append(Spacer(1, 8))

# ColdBloodedShiller
story.append(KeepTogether([
    para('ColdBloodedShiller — @ColdBloodShill', 'h3'),
    para('<b>Source</b>: X tweets Feb 26–Mar 5 (no YouTube videos in window)'),
    para('<b>Key Thesis</b>: Conditionally bullish BTC at key levels. SOL broke out of range with a clear roadmap. 3-month bearish position building in SPX. Gold loading next leg up.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Conditionally Bullish', 'Short-term', '"Hold = good, lose = bad." Strongest RSI momentum push in over a month.'],
    ['Solana', 'Bullish', 'Short-term', 'Broke range resistance. Hold $88 → $100 sweep. Strong → $120. Below $88 = short.'],
    ['S&P 500', 'Bearish', 'Medium (3-month build)', 'Bears need "significant snap of the low." Momentum recently improved for bears.'],
    ['Gold', 'Bullish', 'Medium', '"Next leg up loading." Weekend gold at $5,470.'],
    ['Silver', 'Bullish (partial exit)', 'Medium', '50% TP taken on silver trade.'],
], col_widths=[3*cm, 2.8*cm, 2.8*cm, 6.8*cm]))
story.append(Spacer(1, 8))

# Mercury
story.append(KeepTogether([
    para('Mercury — @TraderMercury', 'h3'),
    para('<b>Sources</b>: X tweets + Discord (#daily-market-update, Feb 27–Mar 4)'),
    para('<b>Key Thesis</b>: Macro bearish — expects BTC weekly lower high then lower low. Short-term watching for relief rally to ~$82K (12H 200MAs) if 4H 200MA inflection point holds. SPY broke below key MAs for first time since May 2025. Closed BTC long. Currently flat.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Watching for $82K / Macro Bearish', 'ST $82K target; MT bearish', '4H 200MAs + local range highs = inflection. Reclaim → $82K. Fail → lower high confirmed, lower low follows.'],
    ['SPY/Equities', 'Bearish', 'Short-term', 'Below 4H 200MAs for first time since May 2025. Broke below year-long trend + multi-month consolidation.'],
    ['Altcoins', 'Neutral (contingent)', 'Short-term', 'If BTC rallies to $82K, expects rotation into alts.'],
], col_widths=[3*cm, 3.6*cm, 2.4*cm, 6.4*cm]))
story.append(para('<i>Discord (Mar 2)</i>: "Whilst the analysis is: we are going to put in a Lower High on the Weekly chart, and then make a Lower Low on all timeframes thereafter, I\'m going to speculate that the 12H 200MAs (~$82K) are the best place to find that Lower High."', 'meta'))
story.append(Spacer(1, 8))

# DonAlt
story.append(KeepTogether([
    para('DonAlt — @DonAlt', 'h3'),
    para('<b>Source</b>: X tweets Feb 26–Mar 5 (no YouTube videos in window)'),
    para('<b>Key Thesis</b>: Neutral — "sitting on hands." BTC had weekly support (bullish signal) but bulls blew the close. Has room to $80K without flipping structurally bullish. Macro/political resolution needed for a meaningful move.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Neutral / Sitting on hands', 'Short-term', '"Bulls had their chance to make the chart look good but looks like they kinda blew it." Room to $80K without flipping bullish.'],
    ['Crypto', 'Neutral to slightly bearish', 'Short-term', '"Chop or down" until US macro/political situation stabilizes.'],
], col_widths=[3*cm, 3.6*cm, 2.4*cm, 6.4*cm]))
story.append(para('<b>Key Level</b>: $80K — reaching it would not itself flip DonAlt structurally bullish.', 'meta'))
story.append(Spacer(1, 8))

# Forward Guidance
story.append(KeepTogether([
    para('Forward Guidance — @ForwardGuidance', 'h3'),
    para('<b>Source</b>: "The AI Productivity Boom Is Here | Luigi Buttiglione" (YouTube, Mar 4) | X tweets Mar 1–5'),
    para('<b>Key Thesis</b>: AI is a genuine, durable productivity boom that raises the neutral interest rate — making rate cuts a policy mistake. Capital rotating from software/tech toward hard assets. U.S. exceptionalism = tech dominance; Europe missed every wave. Near-term economic reacceleration visible in PMIs, manufacturing, and tax refunds.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['US Equities (broad)', 'Neutral/Bullish with caveats', 'Medium', 'Near-term reacceleration signals; "stock picker\'s market, not passive."'],
    ['Software/Tech (IGV)', 'Bearish', 'Medium', 'AI disruption risk makes future cash flows uncertain. Structural multiple reset underway.'],
    ['Hard/Real Assets', 'Bullish', 'Medium', 'Top Q1 2026 ETF inflows. AI forcing rotation to real assets; benefits from reacceleration + inflation risk.'],
    ['Interest Rates', 'Hawkish', 'Medium', 'Productivity boom raises neutral rate. "Cutting rates below neutral would be extremely expensive."'],
    ['Crypto ETFs (most)', 'Bearish', 'Long-term', 'Market flooded with levered/income products — most will end in liquidation.'],
], col_widths=[3.2*cm, 2.8*cm, 2.4*cm, 7*cm]))
story.append(Spacer(1, 8))

# Myles G
story.append(KeepTogether([
    para('Myles G Investments — @MylesGinvest', 'h3'),
    para('<b>Sources</b>: Multiple YouTube videos + X tweets Mar 2–5'),
    para('<b>Key Thesis</b>: BTC has bottomed and a multi-month bull run is starting. Thesis pillars: (1) Coinbase premium flipped positive — last seen at $120K BTC, (2) 200 EMA reclaimed on 4H, (3) 5 consecutive red months historically precede 365%+ pumps, (4) blood moon cycle analog from 2025. Alt season call active.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['BTC', 'Strongly Bullish', 'Days to months', 'Coinbase premium positive, 200 EMA reclaimed, historical analog. Targets: $80K → $98K → $111K'],
    ['XRP', 'Bullish', 'Weeks to months', 'Clarity Act (72% pass prob on PolyMarkets) + X Money launch = massive catalyst. Entry above $1.50, targets $2-3.'],
    ['Altcoins', 'Bullish', 'Near-term', '"Alt season begins now." BTC leads, then rotation.'],
], col_widths=[3*cm, 2.8*cm, 2.6*cm, 7*cm]))
story.append(para('<b>Levels</b>: BTC pullback to $72-73K = long entry. XRP above $1.43, first target $1.67-$1.80, then $2-3.', 'meta'))
story.append(Spacer(1, 8))

# CredibleCrypto
story.append(KeepTogether([
    para('CredibleCrypto — @CredibleCrypto', 'h3'),
    para('<b>Source</b>: X tweets Feb 26–Mar 5 (no YouTube videos in window — last video was Feb 13)'),
    para('<b>Key Thesis</b>: Confident in HTF bottom forming above $50K but explicitly lacks short-term conviction. BTC at confluent resistance in the low $70Ks — the range high is the decision point. Using 2022 Russia/Ukraine fractal: 40%+ bounce before continuation lower.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['BTC', 'Bullish (HTF) / Neutral (STF)', 'HTF bottom above $50K; ST uncertain', 'At range highs — if not ready for expansion, possible rejection. "I don\'t have high confidence in where price is headed short-term."'],
    ['CRV (Curve) / CVX (Convex)', 'Bullish', 'Medium-long', 'Stablecoins at global scale; Curve dominates on-chain swaps. CVX preferred for retail (yield + price appreciation).'],
], col_widths=[3*cm, 3.6*cm, 2.4*cm, 6.4*cm]))
story.append(para('<b>Key Level</b>: Low $70Ks = confluent resistance. Break = expansion. Rejection = possible another leg down within range.', 'meta'))
story.append(Spacer(1, 8))

# Benjamin Cowen
story.append(KeepTogether([
    para('Benjamin Cowen — @intocryptoverse', 'h3'),
    para('<b>Sources</b>: 9 YouTube videos Feb 28–Mar 5 | X tweets Feb 26–Mar 5'),
    para('<b>Key Thesis</b>: Bitcoin is in a midterm year bear market (2026), tracking historical patterns (2014, 2018, 2022) with extraordinary precision. He <i>predicted</i> the current early March rally weeks ago — specifically as evidence <i>for</i> the bear thesis. Prior midterm years: BTC peaked in week 1 of March then resumed lower. Calling this rally a lower high, with lower lows to follow later in 2026. Sold BTC in late 2025. Not re-entering.'),
]))
story.append(Spacer(1, 3))
story.append(make_table([
    ['Asset', 'Stance', 'Timeframe', 'Reasoning'],
    ['Bitcoin', 'Bearish (midterm year bear market)', '6-12 months (all of 2026)', 'Tracking midterm year pattern exactly — 15-16% below yearly open on March 4, matching historical averages. March rally = lower high; lower lows expected later in 2026.'],
    ['Altcoins', 'Bearish', '2026', 'No alt season occurred. Total2 has room to fall toward $1.5T lower regression band from current ~$940B.'],
    ['S&P 500', 'Bearish', '2026', '"Midterm years historically are the weakest year for stocks." SPX not durably moving higher in months.'],
    ['Oil', 'Risk/Concern', 'Near-term', '"Rise of oil in a late business cycle leads to beginning of the end of the business cycle." Geopolitical supply disruption = recession signal.'],
    ['Total Crypto Market Cap', 'Bearish', '2026', 'Currently ~$2.29T; lower regression band ~$1.5T. Room for further downside in midterm year.'],
], col_widths=[3.2*cm, 2.8*cm, 2*cm, 7.4*cm]))
story.append(para('<i>"If your quant who has been bullish on BTC from $126k to $60k is dunking on people because of this candle, then you need to find a new quant. Bitcoin has <b>always</b> rallied in the first week of March in midterm years."</i> — Mar 5, 135K impressions', 'meta'))
story.append(Spacer(1, 10))

# ── Tier 3 ─────────────────────────────────────────────────────────────────
story.append(para('Tier 3 — Brief Mentions (X-Only Traders)', 'h2'))
story.append(section_rule())

t3_rows = [
    ['Trader', 'Asset', 'Stance', 'Note'],
    ['Pentoshi', 'BTC', 'Cautiously Bullish', 'Resilience in face of negative catalysts; historically resolves opposite direction'],
    ['Pentoshi', 'Equities', 'Transitioning bullish', 'Shifting primary focus from crypto to equities long/short'],
    ['Fejau', 'US Economy', 'Bullish (Goldilocks)', 'ISM Services highest since 2022, prices paid at new lows. "Disinflationary growth."'],
    ['Fejau', 'Bonds/TLT', 'Skeptical', 'CT piling into TLT calls is crowded. Prefers SOFR 2028 calls for convexity.'],
    ['Fejau', 'Oil', 'Cautious', 'War priced as short-lived — asymmetric tail risk if conflict drags'],
    ['Follis', 'BTC', 'Short bias (patient)', 'OI up, spot CVD up, funding going negative — wants to short but exercising patience'],
    ['Follis', 'XAG (Silver)', 'Bearish', 'Posted with downward emoji'],
    ['Smiley', 'Broad Markets', 'Short-term bearish', '"Topped for weeks, likely months" — but HTF bull market intact'],
    ['IncomeSharks', 'BTC', 'Neutral/Watching', 'Needs green monthly close to confirm recovery'],
    ['IncomeSharks', 'ETH', 'Cautiously Bullish', 'Positive daily candle; needs SuperTrend confirmation'],
    ['IncomeSharks', 'SPY', 'Neutral/Range', 'Gap-filling complete; VIX at resistance = don\'t fear another April-sized event'],
    ['IncomeSharks', 'HOOD', 'Bullish (long-term)', 'Becoming a full bank. $200 target in years.'],
    ['IncomeSharks', 'Gold', 'Bearish (short-term)', 'Massive single-day selloff; debasement trade overdone'],
    ['CryptoCondom', 'Equities', 'Bearish', 'Buying puts in tranches. "My body is ready. Nuke it."'],
    ['CryptoCondom', 'Uranium', 'Bullish', 'Structural shortage, demand from reactor builds, no supply chain risk'],
    ['PaikCapital', 'BTC', 'Conditionally Bullish', '"Hold 68K on weeklies = macro bottom confirmed."'],
    ['PaikCapital', 'Alts', 'Cautiously Bullish', '3-4 alts showing early alt season signals. ZRO (LayerZero) specific long.'],
    ['ExitLiqNick', 'BTC', 'Tactically Bullish → Bearish', 'Bounce to $72-85K range, then expects dump. "Get people bullish at .382 then dump."'],
    ['ExitLiqNick', 'Equities', 'Short', 'Running short stocks while long crypto (rotation trade)'],
    ['Bluntz', 'SOL', 'Strongly Bullish', '"Bottom likely in. Breakout is when, not if." NEAR showing the path.'],
    ['Bluntz', 'Uranium', 'Very Bullish', '18-year highs on LT contracts. India + Kazatomprom deals, China locking up Bannerman. BMN (ASX) — major breakout expected within 2 weeks.'],
    ['Bluntz', 'Silver', 'Bullish vs Gold', 'Gold/silver ratio likely bottomed; silver to outperform'],
    ['Bluntz', 'Oil', 'Cautious', 'Iran pump = fear spike. Major annual bottom not in yet.'],
    ['Anbessa', 'BTC', 'Bearish', 'Called $60K dip in advance. Now in bear market preservation mode.'],
    ['PlurDaddy', 'Geopolitical Risk', 'Bearish', 'Odds of gradual Iran escalation "high." Market pricing it as one-and-done is a mistake.'],
    ['BattleRhino', 'EWY (Korea ETF)', 'Was short (TP\'d)', 'Profited on 15% crash; took profits. Geopolitical risk was mispriced.'],
    ['BattleRhino', 'Crypto/Indices', 'Neutral', 'Range still undecided. Avoiding index shorts for 5.5 months.'],
    ['CavanXY', 'BTC', 'Cautiously Bullish', '$60-65K discount held via spot buying. $80Ks next target. LTHs not spending = support.'],
    ['CavanXY', 'Nasdaq', 'Bearish', 'Bear flag after rejection. Below 50d and 100d MAs. "Probabilities lean lower."'],
    ['CavanXY', 'ETH', 'Flat', 'Trade at ~$1,950s didn\'t work. Went flat.'],
]
story.append(make_table(t3_rows, col_widths=[2.6*cm, 2.8*cm, 3.4*cm, 6.6*cm]))
story.append(Spacer(1, 4))
story.append(para('<b>No market commentary</b>: Loma, Michael Paik, Feyronn, Giver, Noodles', 'meta'))
story.append(para('<b>Account not found</b>: Blockworks (@Blockworks_)', 'meta'))
story.append(Spacer(1, 10))

# ── Key Themes ─────────────────────────────────────────────────────────────
story.append(para('Key Themes This Week', 'h2'))
story.append(section_rule())

themes = [
    ('The Lower High Debate',
     'The week\'s central question. Bears (Cowen, Loukas, TraderMayne, Mercury) are unified — this BTC bounce to $70-82K is a lower high to sell into. Bulls (Myles G) call it the start of a new leg. Cowen\'s framing is sharpest: he called this rally weeks ago as evidence *for* the bear thesis, comparing it point-by-point to 2022\'s Ukraine invasion bounce.'),
    ('Iran Conflict Reshaping Everything',
     'The dominant macro event. Oil +10-13%, South Korea -12%, bond yields rising, Fed rate cut odds collapsing. Multiple traders (Bluntz, BattleRhino, Fejau, PlurDaddy) actively trading around it. PlurDaddy\'s warning is the most cautionary: escalation odds are higher than the market is pricing. BTC acting as partial haven alongside gold.'),
    ('Real Assets Are the Consensus Trade',
     'Quinn Thompson (long energy since Dec, +20%), Citrini (offshore drilling +50%, AI materials +75%/60%), Insomniac (commodities only clear trade), ColdBloodedShiller (gold bullish), and Bluntz (uranium, silver) all converging on the same rotation. Software/tech facing a structural multiple reset; hard assets absorbing the capital.'),
    ('Uranium Has Independent Conviction',
     'Bluntz and CryptoCondom — independently — are both high-conviction uranium bulls. The case: 18-year highs on long-term contracts, India signed $2.6B deal with Cameco + Kazatomprom, China locking up 60% of Bannerman\'s Etango. Not a geopolitical trade — a structural demand story.'),
    ('Software/Tech Is Being Repriced',
     'Forward Guidance, Quinn Thompson, and Citrini all arriving at the same conclusion via different paths — AI disruption is making future cash flows of SaaS/software businesses harder to trust. IGV falling not because businesses are failing but because risk premiums are rising. The rotation from software to real assets may have multi-year legs.'),
]

for i, (title, body) in enumerate(themes, 1):
    story.append(para(f'<b>{i}. {title}</b>'))
    story.append(para(body))
    story.append(Spacer(1, 4))

story.append(Spacer(1, 6))

# ── Actionable Takeaways ───────────────────────────────────────────────────
story.append(para('Actionable Takeaways', 'h2'))
story.append(section_rule())

takeaways = [
    ('On BTC',
     'The $67-68K (Insomniac, PaikCapital) level is the line between "bottom confirmed" and "another leg lower." Bears (Cowen, Mayne, Mercury) are unanimous: this rally to $70-82K is a lower high to sell into, not chase. The risk/reward of buying this bounce is unfavorable. Wait for either a sustained break above $80K or a flush to lower lows.'),
    ('On Equities',
     'Near-universal bearishness — SPY below key MAs for first time since May 2025, cyclical bear signals, Nasdaq bear flag below 50d/100d. CryptoCondom actively buying puts. The Iran wildcard (oil → inflation → Fed hold → multiple compression) has extended this setup. Wait for geopolitical resolution before adding equity risk.'),
    ('On Real Assets',
     'Quinn Thompson is the most structured expression — long energy (XLE, USO, OIH) + natural gas (EQT, AR, RRC) + gold since December, up 20%, adding on Iran catalyst. Uranium (Bluntz: BMN on ASX; CryptoCondom: structural shortage) looks like the next leg. Silver vs. gold (Bluntz: ratio bottomed) is a specific sub-trade within metals.'),
    ('On the Fed/Macro',
     'March 17-18 FOMC priced as a hold. March 6 NFP (tomorrow) and upcoming CPI are near-term catalysts. Fejau\'s contrarian read: ISM Services highest since 2022, prices paid at new lows = Goldilocks before the Iran shock. Cowen\'s warning is the tail risk: oil going up due to geopolitical supply disruption in a late business cycle historically signals recession.'),
    ('On SOL',
     'Bluntz is making the strongest call — "bottom likely in, breakout is when not if" — using NEAR\'s price action as the leading indicator. ColdBloodedShiller has the level-based setup: hold $88, targets $100 then $120. If BTC rallies to $80K+, SOL is the highest-conviction alt rotation trade among tracked traders.'),
]

for title, body in takeaways:
    story.append(para(f'<b>{title}</b>'))
    story.append(para(body))
    story.append(Spacer(1, 4))

story.append(Spacer(1, 8))
story.append(light_rule())
story.append(para('Brief generated on March 5, 2026', 'meta'))
story.append(para('Sources searched: X/Twitter (via API), Substack (via MCP), YouTube (via MCP + transcripts), bitcoin.live (via MCP), Discord (via MCP where accessible)', 'meta'))
story.append(para('Traders with content found: 26 of 31 tracked', 'meta'))
story.append(para('Traders with no content: Loma, Michael Paik, Feyronn, Giver (no market content), Noodles (no market content), Blockworks (account not found)', 'meta'))

# ── Build PDF ──────────────────────────────────────────────────────────────
output_path = '/Users/maxalderman/Downloads/Investment-Brief-2026-03-05.pdf'

doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    leftMargin=1.8*cm,
    rightMargin=1.8*cm,
    topMargin=1.6*cm,
    bottomMargin=1.6*cm,
    title='Investment Brief — March 5, 2026',
    author='Claude Code',
)

doc.build(story)
print(f"PDF saved to: {output_path}")
