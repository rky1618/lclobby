# Copyright (c) BlackFurniture.
# See LICENSE for details.

from __future__ import print_function
import ctypes
import os
try:
    import winreg
except ImportError:
    import _winreg as winreg
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                     'Software\\Valve\\Steam\\ActiveProcess')
dll_32 = winreg.QueryValueEx(key, 'SteamClientDll')[0]
dll_64 = winreg.QueryValueEx(key, 'SteamClientDll64')[0]
steam_path = os.path.dirname(dll_32)
os.environ["PATH"] += os.pathsep + steam_path

lethal_path = os.path.join(steam_path, 'steamapps', 'common',
                        'Lethal Company')
steamapi_path = os.path.join(lethal_path, 'Lethal Company_Data', 'Plugins', 'x86_64', 'steam_api64.dll')

os.environ['SteamAppId'] = '1966720'
try:
    steam_api = ctypes.cdll.steam_api
    client_dll = dll_32
except OSError:
    try:
        steam_api = ctypes.cdll.steam_api64
        client_dll = dll_64
    except OSError:
        # load from DBD
        try:
            steam_api = ctypes.CDLL(steamapi_path)
            client_dll = dll_64
        except OSError as e:
            print('Could not load steam_api.dll or steam_api64.dll.')
            raise e

SteamAPI_Init = steam_api.SteamAPI_Init
GetHSteamUser = steam_api.SteamAPI_GetHSteamUser
GetHSteamPipe = steam_api.SteamAPI_GetHSteamPipe

try:
    CreateInterface = steam_api.SteamInternal_CreateInterface
    special_createinterface = False
except AttributeError:
    client_dll = ctypes.CDLL(client_dll)
    CreateInterface = client_dll.CreateInterface
    special_createinterface = True
CreateInterface.restype = ctypes.c_void_p

GetISteamMatchmaking = steam_api.SteamAPI_ISteamClient_GetISteamMatchmaking
GetISteamMatchmaking.restype = ctypes.c_void_p
GetISteamUtils = steam_api.SteamAPI_ISteamClient_GetISteamUtils
GetISteamUtils.restype = ctypes.c_void_p
AddRequestLobbyListResultCountFilter = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListResultCountFilter
AddRequestLobbyListFilterSlotsAvailable = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListFilterSlotsAvailable
AddRequestLobbyListDistanceFilter = \
    steam_api.SteamAPI_ISteamMatchmaking_AddRequestLobbyListDistanceFilter
RequestLobbyList = steam_api.SteamAPI_ISteamMatchmaking_RequestLobbyList
RequestLobbyList.restype = ctypes.c_ulonglong
IsAPICallCompleted = steam_api.SteamAPI_ISteamUtils_IsAPICallCompleted
IsAPICallCompleted.restype = ctypes.c_bool
GetAPICallResult = steam_api.SteamAPI_ISteamUtils_GetAPICallResult
GetAPICallResult.restype = ctypes.c_bool
GetLobbyByIndex = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyByIndex
GetLobbyByIndex.restype = ctypes.c_ulonglong
GetNumLobbyMembers = steam_api.SteamAPI_ISteamMatchmaking_GetNumLobbyMembers
GetLobbyDataCount = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyDataCount
GetLobbyDataByIndex = steam_api.SteamAPI_ISteamMatchmaking_GetLobbyDataByIndex
GetLobbyDataByIndex.restype = ctypes.c_bool
InviteUserToLobby = steam_api.SteamAPI_ISteamMatchmaking_InviteUserToLobby
InviteUserToLobby.restype = ctypes.c_bool

steam_api.SteamAPI_Init()
steam_user = GetHSteamUser()
steam_pipe = GetHSteamPipe()
if special_createinterface:
    ret = ctypes.c_int()
    SteamClient = ctypes.c_void_p(CreateInterface(b"SteamClient017",
                                                  ctypes.byref(ret)))
else:
    SteamClient = ctypes.c_void_p(CreateInterface(b"SteamClient017"))
SteamUtils = ctypes.c_void_p(GetISteamUtils(SteamClient, steam_pipe,
                                            b"SteamUtils008"))
SteamMatchmaking = ctypes.c_void_p(
    GetISteamMatchmaking(SteamClient, steam_user, steam_pipe,
                         b"SteamMatchMaking009")
)

BUFFER_SIZE = 256
PLAYERS_FILE = 'players.txt'

class Lobby:
    def __init__(self, lobby_id, members):
        self.lobby_id = lobby_id
        self.members = members
        self.data = {}
        self.get = self.data.get

    def get_int(self, key, default=None):
        try:
            return int(self.data[key])
        except KeyError:
            return default

def get_lobbies():
    locations = {
        'close': 0,
        'default': 1,
        'far': 2,
        'worldwide': 3
    }

    AddRequestLobbyListResultCountFilter(SteamMatchmaking, 500)
    AddRequestLobbyListFilterSlotsAvailable(SteamMatchmaking, 1)
    AddRequestLobbyListDistanceFilter(SteamMatchmaking, locations['worldwide'])
    apicall = ctypes.c_ulonglong(RequestLobbyList(SteamMatchmaking))
    failed = ctypes.c_bool(False)
    while not IsAPICallCompleted(SteamUtils, apicall, ctypes.byref(failed)):
        pass
    ret = ctypes.c_uint32()
    GetAPICallResult(SteamUtils, apicall, ctypes.byref(ret),
                     ctypes.sizeof(ctypes.c_uint32), 510, ctypes.byref(failed))
    lobbies = []
    for i in range(ret.value):
        steam_id = ctypes.c_ulonglong(GetLobbyByIndex(SteamMatchmaking, i))
        members = GetNumLobbyMembers(SteamMatchmaking, steam_id)
        meta_count = GetLobbyDataCount(SteamMatchmaking, steam_id)
        if not meta_count:
            continue
        lobby = Lobby(steam_id.value, members)
        lobbies.append(lobby)
        for ii in range(meta_count):
            key = ctypes.create_string_buffer(BUFFER_SIZE)
            value = ctypes.create_string_buffer(BUFFER_SIZE)
            GetLobbyDataByIndex(SteamMatchmaking, steam_id, ii,
                                key, BUFFER_SIZE,
                                value, BUFFER_SIZE)
            lobby.data[key.value.decode('utf-8')] = value.value.decode('utf-8')
    return lobbies

def main():
    lobbies = get_lobbies()
    for lobby in lobbies:
        print(f"lobby ID: {lobby.lobby_id}")
        print(f"  members: {lobby.members}")
        print(f"  data: {lobby.data}")


if __name__ == '__main__':
    main()
