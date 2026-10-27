function Pandoc(doc)
  if #doc.blocks == 0 then
    return doc
  end

  -- Convert the first H1 heading into the document title
  local first = doc.blocks[1]

  if first.t == "Header" and first.level == 1 then
    doc.meta.title = pandoc.MetaInlines(first.content)
    table.remove(doc.blocks, 1)
  end

  -- Add document metadata
  doc.meta.author = pandoc.MetaInlines({
    pandoc.Str("Mauro J. Sanchirico III"),
    pandoc.LineBreak(),
    pandoc.Str("sanchirico.mauro@gmail.com")
  })

  doc.meta.date = pandoc.MetaInlines({
    pandoc.Str("2026")
  })

  -- Promote remaining headings by one level
  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.level >= 2 then
      block.level = block.level - 1
    end
  end

  return doc
end
