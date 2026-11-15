"""The one stylesheet every screen links to. Colours and sizes come from CSS variables that the
page sets inline; nothing here loads from the network (web fonts are served by render.py)."""

WEB_FONTS = {  # family -> file stem in assets/fonts
    "Inter": "inter", "Roboto": "roboto", "Open Sans": "open-sans", "IBM Plex Sans": "ibm-plex-sans",
    "Source Sans 3": "source-sans-3", "JetBrains Mono": "jetbrains-mono", "Fira Code": "fira-code",
}

FONT_FACES = "".join(
    f'@font-face{{font-family:"{fam}";font-weight:{w};font-style:normal;font-display:block;'
    f'src:url("/fonts/{stem}-{w}.woff2") format("woff2")}}'
    for fam, stem in WEB_FONTS.items() for w in (400, 500, 600, 700)
)

BASE_CSS = FONT_FACES + r"""
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden}
body{font-family:var(--font);font-size:var(--fs);line-height:1.35;color:var(--fg);background:var(--bg);cursor:default;user-select:none;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
svg.i{width:var(--is);height:var(--is);stroke:currentColor;fill:none;stroke-width:var(--isw);stroke-linecap:round;stroke-linejoin:round;flex:none;display:block}
.row{display:flex;align-items:center}.col{display:flex;flex-direction:column}.f1{flex:1 1 0;min-width:0;min-height:0}.sp{flex:1 1 0}.fn{flex:none}
.g2{gap:2px}.g4{gap:4px}.g6{gap:6px}.g8{gap:8px}.g10{gap:10px}.g12{gap:12px}.g16{gap:16px}.g24{gap:24px}
.wrap{flex-wrap:wrap}.top{align-items:flex-start}.str{align-items:stretch}.cen{justify-content:center}.btw{justify-content:space-between}.end{justify-content:flex-end}
.el{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}.nw{white-space:nowrap}.clip{overflow:hidden}
.mut{color:var(--fg1)}.fnt{color:var(--fg2)}.acc{color:var(--ac)}.ok{color:var(--ok)}.wrn{color:var(--warn)}.err{color:var(--err)}
.b{font-weight:600}.m{font-weight:500}.sm{font-size:.92em}.xs{font-size:.85em}.lg{font-size:1.15em}.xl{font-size:1.4em}.xxl{font-size:1.8em}
.mono{font-family:var(--mono)}.up{text-transform:uppercase;letter-spacing:.04em}.rt{text-align:right}.ct{text-align:center}
.p4{padding:4px}.p6{padding:6px}.p8{padding:8px}.p12{padding:12px}.p16{padding:16px}.p20{padding:20px}.p24{padding:24px}
.px8{padding-left:8px;padding-right:8px}.px12{padding-left:12px;padding-right:12px}.px16{padding-left:16px;padding-right:16px}.py4{padding-top:4px;padding-bottom:4px}.py8{padding-top:8px;padding-bottom:8px}
.bb{border-bottom:1px solid var(--bd)}.bt{border-top:1px solid var(--bd)}.bl{border-left:1px solid var(--bd)}.br{border-right:1px solid var(--bd)}.ba{border:1px solid var(--bd)}
.bg{background:var(--bg)}.bg1{background:var(--bg1)}.bg2{background:var(--bg2)}.bg3{background:var(--bg3)}.rad{border-radius:var(--r)}.rad2{border-radius:var(--r2)}
.rel{position:relative}.h100{height:100%}.w100{width:100%}

/* desktop and window */
#desk{position:fixed;inset:0;display:flex;flex-direction:column;background:var(--wall)}
#win{position:relative;flex:1 1 0;min-height:0;display:flex;flex-direction:column;background:var(--bg);overflow:hidden}
#win.float{border-radius:var(--wr);box-shadow:0 22px 70px rgba(0,0,0,.42),0 0 0 1px rgba(0,0,0,.28)}
#stage{flex:1 1 0;min-height:0;display:flex;flex-direction:column}
#stage.inset{padding:var(--inset)}
.osbar{flex:none;height:26px;display:flex;align-items:center;padding:0 10px;gap:14px;font-size:13px;color:#f2f2f2;background:rgba(20,20,24,.72)}
.osbar.light{color:#1c1c1e;background:rgba(246,246,246,.86)}
.osbar .mb{padding:0 2px}.osbar svg.i{width:15px;height:15px}
.taskbar{flex:none;height:44px;display:flex;align-items:center;gap:4px;padding:0 10px;background:rgba(28,30,38,.92);color:#eee}
.taskbar.light{background:rgba(238,241,246,.95);color:#1b1b1b}
.taskbar .ti{width:36px;height:36px;border-radius:5px;display:flex;align-items:center;justify-content:center}
.taskbar .ti.on{background:rgba(127,127,127,.25);box-shadow:inset 0 -2px 0 var(--ac)}
.taskbar svg.i{width:20px;height:20px}
.dock{flex:none;align-self:center;display:flex;gap:6px;padding:5px 7px;margin:6px 0 6px;border-radius:16px;background:rgba(240,240,244,.35);box-shadow:0 0 0 1px rgba(255,255,255,.25),0 6px 20px rgba(0,0,0,.25)}
.dock .di{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff}
.dock svg.i{width:22px;height:22px}

/* title bars */
.tbar{flex:none;display:flex;align-items:center;background:var(--bg2);border-bottom:1px solid var(--bd);position:relative}
.tbar.mac{height:var(--tbh,38px);padding:0 12px;gap:8px}
.tbar .ttl{position:absolute;left:0;right:0;text-align:center;font-weight:600;color:var(--fg1);font-size:13px}
.tbar .ttl span{background:transparent}
.lights{display:flex;gap:8px;align-items:center;z-index:1}
.lights>div{width:12px;height:12px;border-radius:50%;box-shadow:inset 0 0 0 .5px rgba(0,0,0,.25)}
.lights .c{background:#ff5f57}.lights .n{background:#febc2e}.lights .x{background:#28c840}
.tbar.win{height:32px;padding-left:10px;gap:8px;font-size:12px}
.tbar.win .wc{display:flex;align-self:stretch;margin-left:auto}
.tbar.win .wc>div{width:46px;display:flex;align-items:center;justify-content:center;color:var(--fg)}
.tbar.win .wc svg{width:10px;height:10px;stroke:currentColor;fill:none;stroke-width:1}
.tbar.gnome{height:44px;padding:0 8px;gap:6px}
.tbar.gnome .gc{display:flex;gap:8px;margin-left:6px}
.tbar.gnome .gc>div{width:24px;height:24px;border-radius:50%;background:var(--bg4);display:flex;align-items:center;justify-content:center;color:var(--fg)}
.tbar.gnome .gc svg{width:10px;height:10px;stroke:currentColor;fill:none;stroke-width:1.4}
.appico{width:16px;height:16px;border-radius:4px;background:var(--ac);flex:none}
.mbar{flex:none;display:flex;align-items:center;height:calc(var(--ch) + 2px);padding:0 6px;background:var(--bg2);border-bottom:1px solid var(--bd);gap:2px}
.mb{padding:0 8px;height:100%;display:flex;align-items:center;border-radius:var(--r);white-space:nowrap}
.mb.open,.open.mb{background:var(--acs2)}
/* browser frame */
.btabs{flex:none;display:flex;align-items:flex-end;height:38px;background:var(--bg2);padding:0 8px;gap:2px}
.btab{display:flex;align-items:center;gap:8px;height:30px;padding:0 10px;min-width:120px;max-width:220px;border-radius:8px 8px 0 0;color:var(--fg1);font-size:12px}
.btab.on{background:var(--bg1);color:var(--fg)}
.btab .fav{width:14px;height:14px;border-radius:3px;flex:none}
.burl{flex:none;display:flex;align-items:center;gap:6px;height:38px;padding:0 10px;background:var(--bg1);border-bottom:1px solid var(--bd)}
.burl .url{flex:1;height:28px;border-radius:14px;background:var(--bg3);display:flex;align-items:center;gap:8px;padding:0 12px;font-size:12.5px;color:var(--fg1);min-width:0}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:var(--ch);padding:0 var(--cp);border-radius:var(--r);border:1px solid var(--bd2);background:var(--bg);color:var(--fg);white-space:nowrap;font-weight:500;flex:none}
.s-soft .btn{border-color:transparent;background:var(--bg4)}
.s-flat .btn{border-color:transparent;background:transparent}
.btn.pri{background:var(--ac);border-color:var(--ac);color:var(--acf)}
.btn.ghost{border-color:transparent;background:transparent}
.btn.out{border-color:var(--bd2);background:transparent}
.btn.dng{color:var(--err)}
.btn.sm{height:calc(var(--ch) - 4px);padding:0 8px;font-size:.92em}
.btn.lgb{height:calc(var(--ch) + 8px);padding:0 16px}
.btn svg.i{width:calc(var(--is) - 1px);height:calc(var(--is) - 1px)}
.ib{display:inline-flex;align-items:center;justify-content:center;width:var(--ibs);height:var(--ibs);border-radius:var(--r);color:var(--fg1);flex:none}
.ib.on{background:var(--acs2);color:var(--ac)}
.ib.bdr{border:1px solid var(--bd2);color:var(--fg)}
.ib.fill{background:var(--ac);color:var(--acf)}
.ib.s{width:calc(var(--ibs) - 6px);height:calc(var(--ibs) - 6px)}.ib.s svg.i{width:calc(var(--is) - 2px);height:calc(var(--is) - 2px)}
.ib.l{width:calc(var(--ibs) + 8px);height:calc(var(--ibs) + 8px)}.ib.l svg.i{width:calc(var(--is) + 4px);height:calc(var(--is) + 4px)}
.ib.rnd{border-radius:50%}
.vsep{width:1px;align-self:stretch;margin:4px 4px;background:var(--bd);flex:none}
.hsep{height:1px;background:var(--bd);flex:none}
.tb{flex:none;display:flex;align-items:center;gap:4px;padding:4px 8px;background:var(--bg1);border-bottom:1px solid var(--bd);min-height:calc(var(--ch) + 10px)}
.tb.plain{background:var(--bg)}

/* inputs */
.inp{display:flex;align-items:center;gap:6px;height:var(--ch);padding:0 8px;border:1px solid var(--bd2);border-radius:var(--r);background:var(--inp);color:var(--fg);min-width:0;white-space:nowrap}
.inp.rnd{border-radius:999px;padding:0 12px}.inp.soft{border-color:transparent;background:var(--bg3)}
.inp.area{height:auto;align-items:flex-start;padding:6px 8px;white-space:normal}
.inp.foc{border-color:var(--ac);box-shadow:0 0 0 2px var(--acs2)}
.inp .ph{color:var(--fg2)}.inp svg.i{color:var(--fg2);width:calc(var(--is) - 2px);height:calc(var(--is) - 2px)}
.inp .car{width:1px;height:1.2em;background:var(--fg);margin-left:-5px}
.lbl{font-size:.92em;color:var(--fg1);margin-bottom:4px;font-weight:500}
.chk{display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.chk .box{width:15px;height:15px;border:1.5px solid var(--bd2);border-radius:3px;display:flex;align-items:center;justify-content:center;background:var(--inp);flex:none;color:transparent}
.chk .box svg{width:11px;height:11px;stroke:currentColor;fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.chk.on .box{background:var(--ac);border-color:var(--ac);color:var(--acf)}
.chk.rd .box{border-radius:50%}.chk.rd.on .box{background:var(--inp);box-shadow:inset 0 0 0 3px var(--ac);border-color:var(--ac)}
.tog{width:34px;height:20px;border-radius:10px;background:var(--bd2);position:relative;flex:none}
.tog::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.3)}
.tog.on{background:var(--ac)}.tog.on::after{left:16px}
.tog.sq{border-radius:4px}.tog.sq::after{border-radius:2px}
.sld{position:relative;height:16px;flex:1;min-width:60px}
.sld::before{content:"";position:absolute;left:0;right:0;top:6px;height:4px;border-radius:2px;background:var(--bg4)}
.sld .fill{position:absolute;left:0;top:6px;height:4px;border-radius:2px;background:var(--ac)}
.sld .th{position:absolute;top:1px;width:14px;height:14px;margin-left:-7px;border-radius:50%;background:#fff;border:1px solid var(--bd2);box-shadow:0 1px 2px rgba(0,0,0,.25)}
.seg{display:inline-flex;border:1px solid var(--bd2);border-radius:var(--r);background:var(--bg);flex:none}
.seg>div{padding:0 10px;height:calc(var(--ch) - 2px);display:flex;align-items:center;gap:5px;border-left:1px solid var(--bd);white-space:nowrap;color:var(--fg1)}
.seg>div:first-child{border-left:none;border-radius:var(--r) 0 0 var(--r)}.seg>div:last-child{border-radius:0 var(--r) var(--r) 0}
.seg>.on{background:var(--acs2);color:var(--fg);font-weight:500}
.step{display:inline-flex;border:1px solid var(--bd2);border-radius:var(--r);height:var(--ch);align-items:stretch;background:var(--inp)}
.step>div{display:flex;align-items:center;justify-content:center;min-width:22px;padding:0 4px}.step .v{min-width:34px;border-left:1px solid var(--bd);border-right:1px solid var(--bd)}
.sw{width:18px;height:18px;border-radius:4px;border:1px solid var(--bd2);flex:none}

/* lists, nav, tabs */
.nav{display:flex;align-items:center;gap:8px;height:var(--rh);padding:0 10px;margin:0 6px;border-radius:var(--r);color:var(--fg);white-space:nowrap;flex:none}
.nav svg.i{color:var(--fg1)}
.nav.on{background:var(--acs2)}.n-solid .nav.on{background:var(--ac);color:var(--acf)}.n-solid .nav.on svg.i,.n-solid .nav.on .cnt{color:var(--acf)}
.n-bar .nav.on{background:var(--bg3);box-shadow:inset 3px 0 0 var(--ac);border-radius:0;margin:0;padding-left:16px}
.nav .cnt{margin-left:auto;font-size:.85em;color:var(--fg2)}
.hd{font-size:.82em;font-weight:600;color:var(--fg2);text-transform:uppercase;letter-spacing:.05em;padding:10px 16px 4px;white-space:nowrap}
.side{flex:none;display:flex;flex-direction:column;background:var(--bg1);overflow:hidden}
.side.dk{background:var(--sdk);color:var(--sdkf)}.side.dk .nav{color:var(--sdkf)}.side.dk .nav svg.i,.side.dk .hd,.side.dk .cnt,.side.dk .mut,.side.dk .fnt{color:var(--sdkm)}.side.dk .nav.on{background:rgba(255,255,255,.16);color:#fff}.side.dk .ib{color:var(--sdkm)}
.rail{flex:none;display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px 0;background:var(--bg2);width:calc(var(--ibs) + 20px)}
.rail .ib{width:calc(var(--ibs) + 8px);height:calc(var(--ibs) + 8px)}.rail .ib svg.i{width:calc(var(--is) + 4px);height:calc(var(--is) + 4px)}
.tabs{flex:none;display:flex;align-items:stretch;border-bottom:1px solid var(--bd);padding:0 8px;gap:2px}
.tab{display:flex;align-items:center;gap:6px;padding:0 12px;height:calc(var(--ch) + 8px);color:var(--fg1);border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap;font-weight:500}
.tab.on{color:var(--fg);border-bottom-color:var(--ac)}
.tabs.box{padding:0;gap:0;background:var(--bg1)}
.tabs.box .tab{border-right:1px solid var(--bd);border-bottom:none;margin:0;font-weight:400;height:calc(var(--ch) + 10px)}
.tabs.box .tab.on{background:var(--bg);box-shadow:inset 0 2px 0 var(--ac)}
.tabs.pl{border-bottom:none;padding:6px 8px;gap:4px}
.tabs.pl .tab{border:none;margin:0;border-radius:999px;height:var(--ch)}.tabs.pl .tab.on{background:var(--acs2);color:var(--fg)}
.tab .x{display:flex;border-radius:3px;color:var(--fg2)}.tab .x svg.i{width:12px;height:12px}
.tr{display:flex;align-items:center;min-height:var(--rh);border-bottom:1px solid var(--bd);flex:none}
.tr.h{background:var(--bg1);color:var(--fg1);font-weight:600;font-size:.9em}
.tr.sel{background:var(--acs)}.tr.z:nth-child(even){background:var(--bg1)}
.td{padding:0 10px;flex:none;display:flex;align-items:center;gap:6px;min-width:0;align-self:stretch}
.td.f{flex:1 1 0}.td.r{justify-content:flex-end}
.li{display:flex;align-items:center;gap:8px;min-height:var(--rh);padding:0 10px;flex:none}
.li.sel{background:var(--acs)}
.pill{display:inline-flex;align-items:center;gap:4px;height:1.6em;padding:0 8px;border-radius:999px;font-size:.85em;font-weight:500;background:var(--bg4);color:var(--fg1);white-space:nowrap;flex:none}
.pill.g{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}.pill.y{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
.pill.r{background:color-mix(in srgb,var(--err) 16%,transparent);color:var(--err)}.pill.a{background:var(--acs2);color:var(--ac)}
.bdg{display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:var(--ac);color:var(--acf);font-size:10px;font-weight:700;flex:none}
.av{display:inline-flex;align-items:center;justify-content:center;border-radius:50%;color:#fff;font-weight:600;flex:none;width:24px;height:24px;font-size:10px}
.av.sq{border-radius:6px}
.kb{font-size:.86em;color:var(--fg2);white-space:nowrap}
.card{background:var(--bg);border:1px solid var(--bd);border-radius:var(--r2)}
.dot{width:8px;height:8px;border-radius:50%;flex:none}
.scr{position:absolute;right:2px;width:6px;border-radius:3px;background:var(--bd2);opacity:.8}
.sbar{flex:none;display:flex;align-items:center;gap:12px;height:22px;padding:0 10px;font-size:11.5px;background:var(--bg2);border-top:1px solid var(--bd);color:var(--fg1);white-space:nowrap}
.sbar.acc{background:var(--ac);color:var(--acf);border-top:none}
.sbar .si{display:flex;align-items:center;gap:4px;height:100%}.sbar svg.i{width:12px;height:12px}
.prog{height:6px;border-radius:3px;background:var(--bg4);overflow:hidden}.prog>div{height:100%;background:var(--ac)}
.thumb{border-radius:var(--r);background:linear-gradient(135deg,var(--c1,#6b8cff),var(--c2,#b76bff));flex:none}

/* overlays */
.ovl{position:fixed;z-index:1000}
.menu{min-width:190px;padding:4px;background:var(--pop);border:1px solid var(--bd);border-radius:max(4px,var(--r2));box-shadow:0 10px 32px var(--sh),0 2px 6px var(--sh);color:var(--fg)}
.mi{display:flex;align-items:center;gap:8px;height:calc(var(--rh) + 2px);padding:0 10px;border-radius:max(2px,calc(var(--r) - 1px));white-space:nowrap}
.mi.on{background:var(--ac);color:var(--acf)}.mi.on .kb,.mi.on svg.i{color:var(--acf)}
.mi .kb{margin-left:auto;padding-left:28px}.mi svg.i{width:calc(var(--is) - 2px);height:calc(var(--is) - 2px);color:var(--fg1)}
.mi.dis{color:var(--fg2)}.mi .ck{width:14px;flex:none}
.msep{height:1px;background:var(--bd);margin:4px 2px}
.mhd{font-size:.82em;color:var(--fg2);padding:4px 10px 2px;font-weight:600}
.back{position:absolute;inset:0;background:rgba(0,0,0,.42);display:flex;align-items:center;justify-content:center;z-index:900}
.back.topa{align-items:flex-start}.back.righta{justify-content:flex-end;align-items:stretch}
.dlg{background:var(--bg);border:1px solid var(--bd);border-radius:max(6px,var(--r2));box-shadow:0 24px 80px rgba(0,0,0,.5);display:flex;flex-direction:column;overflow:hidden;color:var(--fg)}
.dlg .dh{display:flex;align-items:center;gap:8px;padding:14px 16px 10px;font-weight:600;font-size:1.12em}
.dlg .db{padding:4px 16px 14px;display:flex;flex-direction:column;gap:12px}
.dlg .df{display:flex;align-items:center;justify-content:flex-end;gap:8px;padding:12px 16px;background:var(--bg1);border-top:1px solid var(--bd)}
.tip{background:#16181d;color:#f4f4f5;padding:4px 8px;border-radius:5px;font-size:.88em;white-space:nowrap;box-shadow:0 4px 14px rgba(0,0,0,.35)}
.tip.lt{background:#fffbe6;color:#222;border:1px solid #cfcab0}
"""
