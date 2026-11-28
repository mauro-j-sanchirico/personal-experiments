local function extract_abstract(blocks, meta)
  for index, block in ipairs(blocks) do
    if block.t == "Div" and extract_abstract(block.content, meta) then
      return true
    end
    if block.t == "Para" and block.content[1] and block.content[1].t == "Strong"
      and pandoc.utils.stringify(block.content[1].content) == "Abstract"
      and block.content[2] and block.content[2].t == "Str"
      and block.content[2].text == ":" then
      local content = block.content
      content:remove(1)
      content:remove(1)
      if content[1] and content[1].t == "Space" then content:remove(1) end
      meta.abstract = pandoc.MetaBlocks({ pandoc.Para(content) })
      table.remove(blocks, index)
      if blocks[index] and blocks[index].t == "HorizontalRule" then
        table.remove(blocks, index)
      end
      if index > 1 and blocks[index - 1].t == "HorizontalRule" then
        table.remove(blocks, index - 1)
      end
      return true
    end
  end
  return false
end

function Pandoc(doc)
  extract_abstract(doc.blocks, doc.meta)
  return doc
end
