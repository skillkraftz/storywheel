" Manuscript text: *italic* and **bold**, with the marks concealed. A scene break line `* * *` is drawn by
" extmarks (sw/prose.lua), so nothing here may treat its asterisks as italic.
if exists("b:current_syntax")
  finish
endif
syntax region swItalic matchgroup=swMark start=/\*\ze[^* ]/ end=/[^* ]\zs\*/ concealends oneline
syntax region swBold matchgroup=swMark start=/\*\*\ze[^* ]/ end=/[^* ]\zs\*\*/ concealends oneline
highlight default swItalic gui=italic cterm=italic
highlight default swBold gui=bold cterm=bold
highlight default link swMark Conceal
let b:current_syntax = "storywheel"
