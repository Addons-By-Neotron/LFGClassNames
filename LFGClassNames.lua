-- Adds a class icon and the class name to each member in the group finder's
-- listing tooltip, which otherwise shows the class only as the colour of the
-- name. LFG Forever shows Blizzard's same tooltip, so it gets them too.

local canaccess = canaccessvalue or function() return true end

local function Readable(value)
	return value ~= nil and canaccess(value)
end

local ADDON = ...
local hooked = false
local DEFAULTS = { showIcon = true, showName = true }
local db = DEFAULTS  -- (the saved settings once loaded)

-- "<icon> Name  Class" (as the settings ask), or nil when the class can't be read.
local function Label(info)
	if not info or not Readable(info.name) or not Readable(info.classFilename) then
		return nil
	end
	local class = info.classFilename
	local text = info.name
	if db.showIcon then
		text = ("|A:groupfinder-icon-class-%s:14:14|a %s"):format(class:lower(), text)
	end
	if db.showName then
		local className = (LOCALIZED_CLASS_NAMES_MALE and LOCALIZED_CLASS_NAMES_MALE[class]) or class
		text = ("%s  |cffd8d8d8%s|r"):format(text, className)
	end
	return text
end

local function Decorate(tooltip, resultID)
	if not db.showIcon and not db.showName then
		return
	end
	local result = C_LFGList.GetSearchResultInfo(resultID)
	if not result or not Readable(result.numMembers) then
		return
	end

	-- the members by name: the rows of the pool are not in member order
	local byName = {}
	for i = 1, result.numMembers do
		local info = C_LFGList.GetSearchResultPlayerInfo(resultID, i)
		if info and Readable(info.name) then
			byName[info.name] = info
		end
	end

	local rows = {}
	if tooltip.Leader and tooltip.Leader:IsShown() then
		rows[#rows + 1] = { tooltip.Leader, C_LFGList.GetSearchResultLeaderInfo(resultID) }
	end
	for frame in tooltip.memberPool:EnumerateActive() do
		local text = frame.Name:GetText()
		if Readable(text) then
			rows[#rows + 1] = { frame, byName[text] }
		end
	end

	local oldWidth = tooltip.Leader.Name:GetWidth()
	local changed = false
	for _, row in ipairs(rows) do
		local label = Label(row[2])
		if label then
			row[1].Name:SetWidth(0)
			row[1].Name:SetText(label)
			changed = true
		end
	end
	if not changed then
		return
	end

	-- every name as wide as the widest, as Blizzard lines them up, and the
	-- tooltip wider by as much as the names grew
	local width = 0
	for _, row in ipairs(rows) do
		width = math.max(width, row[1].Name:GetStringWidth())
	end
	for _, row in ipairs(rows) do
		row[1].Name:SetWidth(width)
	end
	if Readable(oldWidth) and width > oldWidth then
		tooltip:SetWidth(tooltip:GetWidth() + width - oldWidth)
	end
end

local function Hook()
	if hooked or not LFGBrowseSearchEntryTooltip_UpdateAndShow then
		return
	end
	hooksecurefunc("LFGBrowseSearchEntryTooltip_UpdateAndShow", Decorate)
	hooked = true
end

local category
local function RegisterSettings()
	category = Settings.RegisterVerticalLayoutCategory("LFG Class Names")
	local function Checkbox(key, name, tooltip)
		local setting = Settings.RegisterAddOnSetting(category, "LFGClassNames_" .. key, key, db, "boolean", name, DEFAULTS[key])
		Settings.CreateCheckbox(category, setting, tooltip)
	end
	Checkbox("showIcon", "Show class icon", "Show the class icon before each name in the group finder's tooltip.")
	Checkbox("showName", "Show class name", "Show the class name after each name in the group finder's tooltip.")
	Settings.RegisterAddOnCategory(category)
end

SLASH_LFGCLASSNAMES1 = "/lfgcn"
SlashCmdList.LFGCLASSNAMES = function()
	if category then
		Settings.OpenToCategory(category:GetID())
	end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("ADDON_LOADED")
frame:SetScript("OnEvent", function(_, _, name)
	if name == ADDON then
		LFGClassNamesDB = LFGClassNamesDB or {}
		db = LFGClassNamesDB
		for key, value in pairs(DEFAULTS) do
			if db[key] == nil then db[key] = value end
		end
		RegisterSettings()
	end
	Hook()  -- (the group finder is loaded on demand)
end)
Hook()
