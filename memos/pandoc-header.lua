function Meta(meta)
  local file = assert(io.open("pandoc-header.tex", "r"))
  local header = file:read("*a")
  file:close()
  meta["header-includes"] = meta["header-includes"] or pandoc.MetaList({})
  meta["header-includes"]:insert(pandoc.MetaBlocks({pandoc.RawBlock("latex", header)}))
  return meta
end
