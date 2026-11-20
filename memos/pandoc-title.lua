local function read_metadata(block, meta)
  if not block or block.t ~= "Para" then
    return false
  end

  local values = {}
  local key = nil
  for _, inline in ipairs(block.content) do
    if inline.t == "LineBreak" or inline.t == "SoftBreak" then
      key = nil
    elseif not key then
      if inline.t ~= "Strong" then return false end
      local label = pandoc.utils.stringify(inline.content)
      key = ({ ["Authors:"] = "author", ["Published:"] = "date", ["Copyright Year:"] = "copyright-year", ["Copyright Name:"] = "copyright-name" })[label]
      if not key then return false end
      values[key] = pandoc.List()
    elseif #values[key] > 0 or inline.t ~= "Space" then
      values[key]:insert(inline)
    end
  end

  for name, value in pairs(values) do
    if #value == 0 then return false end
    meta[name] = pandoc.MetaInlines(value)
  end
  return next(values) ~= nil
end

local function remove_metadata(blocks, meta)
  while read_metadata(blocks[1], meta) do
    table.remove(blocks, 1)
  end
end

function Pandoc(doc)
  if #doc.blocks == 0 then
    return doc
  end

  -- Convert the first H1 heading into the document title
  local first = doc.blocks[1]
  local title_blocks = doc.blocks
  if first.t == "Div" and first.classes:includes("markdown") then
    title_blocks = first.content
    first = title_blocks[1]
  end

  if first and first.t == "Header" and first.level == 1 then
    doc.meta.title = pandoc.MetaInlines(first.content)
    table.remove(title_blocks, 1)
    remove_metadata(title_blocks, doc.meta)
    if title_blocks ~= doc.blocks and #title_blocks == 0 then
      local next_cell = doc.blocks[2]
      if next_cell and next_cell.t == "Div" and next_cell.classes:includes("markdown") then
        remove_metadata(next_cell.content, doc.meta)
      end
    end
  end

  -- Promote remaining headings by one level
  doc = doc:walk({
    Header = function(header)
      if header.level >= 2 then
        header.level = header.level - 1
      end
      return header
    end
  })

  return doc
end
