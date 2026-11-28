function Meta(meta)
  local file = assert(io.open("pdf_builder/pandoc-header.tex", "r"))
  local header = file:read("*a")
  file:close()
  meta["header-includes"] = meta["header-includes"] or pandoc.MetaList({})
  meta["header-includes"]:insert(pandoc.MetaBlocks({pandoc.RawBlock("latex", header)}))
  return meta
end

function Header(header)
  if header.level ~= 1 then
    return
  end

  local title = pandoc.utils.stringify(header.content)
  if title == "References" then
    header.classes:insert("unnumbered")
    return { pandoc.RawBlock("latex", "\\clearpage"), header }
  elseif title == "Appendix" then
    header.classes:insert("unnumbered")
    return { pandoc.RawBlock("latex", "\\clearpage\n\\appendix\n\\setcounter{section}{1}"), header }
  end
end
