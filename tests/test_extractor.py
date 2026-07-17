import pytest
from roblox_string_scrapper.extractor import (
    extract_asset_urls,
    extract_remote_names,
    extract_lua_snippets,
    extract_all,
)


def test_extract_asset_urls():
    sample = (
        "local mesh = 'rbxassetid://12345678'\n"
        "local sound = 'http://www.roblox.com/asset/?id=987654321'\n"
        "local texture = 'https://assetdelivery.roblox.com/v1/asset/?id=555444333'\n"
        "local thumb = 'rbxthumb://type=Asset&id=777888999&w=150&h=150'\n"
        "local random_noise = 'foobar123'"
    )
    urls = extract_asset_urls(sample)
    assert len(urls) == 4
    assert "rbxassetid://12345678" in urls
    assert "http://www.roblox.com/asset/?id=987654321" in urls
    assert "https://assetdelivery.roblox.com/v1/asset/?id=555444333" in urls
    assert "rbxthumb://type=Asset&id=777888999&w=150&h=150" in urls


def test_extract_remote_names():
    sample = (
        "ReplicatedStorage:WaitForChild('AdminBroadcastEvent'):FireServer()\n"
        "local rf = game.ReplicatedStorage.RemoteFunctions.RequestInventory\n"
        "local bad_var = 'just_some_normal_string'\n"
        "Network:FireServer('PlayerDamageTake', 25)\n"
        "Remotes.InventoryUpdate:InvokeServer()\n"
        "BindableEvent:Fire('local_hud_sync')"
    )
    remotes = extract_remote_names(sample)
    assert "AdminBroadcastEvent" in remotes
    assert "PlayerDamageTake" in remotes
    assert "RequestInventory" in remotes
    assert "InventoryUpdate" in remotes
    assert "local_hud_sync" in remotes
    assert "just_some_normal_string" not in remotes


def test_extract_lua_snippets():
    sample = (
        "GARBAGEBINARY123\x00\x01\x02" 
        "function OnPlayerAdded(player)\n" 
        "    local leaderstats = Instance.new('Folder')\n" 
        "    leaderstats.Name = 'leaderstats'\n" 
        "    leaderstats.Parent = player\n" 
        "end\n" 
        "BINARYREST456\xff\xfe"
    )
    scripts = extract_lua_snippets(sample)
    assert len(scripts) >= 1
    assert "function OnPlayerAdded" in scripts[0]
    assert "leaderstats.Parent = player" in scripts[0]


def test_extract_all_aggregates():
    raw_input = (
        "local e = 'rbxassetid://9999'\n"
        "Remotes.CombatHit:FireServer()\n"
        "-- normal string payload\n"
        "local msg = 'hello world'"
    )
    res = extract_all(raw_input, filter_junk=True)
    assert "rbxassetid://9999" in res["urls"]
    assert "CombatHit" in res["remotes"]
