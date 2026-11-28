function Meta(meta)
  if not meta["copyright-year"] then
    return meta
  end

  local year = pandoc.utils.stringify(meta["copyright-year"])
  if not year:match("^%d%d%d%d$") then
    error("Copyright Year must be a four-digit year")
  end
  if not meta["copyright-name"] then
    error("Copyright Name is required when Copyright Year is set")
  end
  local name = pandoc.write(pandoc.Pandoc({pandoc.Plain(meta["copyright-name"])}), "latex"):gsub("%s+$", "")

  local footer = [[
\usepackage{fancyhdr}
\fancyhf{}
\fancyfoot[C]{{\footnotesize \copyright{} ]] .. year .. " " .. name .. [[}\\[3pt]\thepage}
\renewcommand{\headrulewidth}{0pt}
\pagestyle{fancy}
\fancypagestyle{plain}{\pagestyle{fancy}}
]]
  meta["header-includes"] = meta["header-includes"] or pandoc.MetaList({})
  meta["header-includes"]:insert(pandoc.MetaBlocks({pandoc.RawBlock("latex", footer)}))
  return meta
end
