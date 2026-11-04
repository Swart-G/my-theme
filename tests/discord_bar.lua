local captured = {}
local watcher
local config = {glyph = 'brand-discord'}
local state = {status='discord_unavailable', participants={}, voice={mute=false,deaf=false}}
utf8 = {len=string.len, offset=function(_,n) return n end}
barWidget = {
  setVisible=function(v) captured.visible=v end,
  setGlyph=function(v) captured.glyph=v end,
  setGlyphColor=function(v) captured.color=v end,
  setText=function(v) captured.text=v end,
  setTooltip=function(v) captured.tooltip=v end,
}
noctalia = {
 state={get=function() return state end,watch=function(_,fn) watcher=fn end},
 tr=function(key) return key end,
 getConfig=function(key) return config[key] end,
}
dofile(arg[1])
assert(captured.glyph=='brand-discord' and captured.text=='' and captured.visible)
assert(captured.tooltip=='bar.offline')
state.channel={name='Voice'}; state.status='connected'; state.participants={{speaking=true,avatar_path='/tmp/test-avatar.png'}}
watcher(state)
assert(captured.glyph=='brand-discord' and captured.color=='primary')
assert(captured.text=='Voice 1')
state.participants[1].speaking=false; state.voice.mute=true
watcher(state)
assert(captured.glyph=='brand-discord' and captured.color=='error')
state.channel=nil; state.status='auth_required'; state.participants={}
watcher(state)
assert(captured.text=='' and captured.tooltip=='bar.authorize')
config.hide_when_disconnected=true; watcher(state); assert(captured.visible==false)
config.hide_when_disconnected=false; watcher(state); assert(captured.visible==true)
print('Discord native glyph stays stable across voice transitions')
