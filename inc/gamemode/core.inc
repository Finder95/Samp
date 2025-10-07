#if defined _CORE_MODULE_INCLUDED
    #endinput
#endif
#define _CORE_MODULE_INCLUDED

#define SERVER_NAME "Profesjonalny Projekt RP"
#define SERVER_VERSION "1.0.0"
#define SERVER_DB_FILE "scriptfiles/projekt.db"

#define COLOR_WHITE 0xFFFFFFFF
#define COLOR_INFO 0x00B9FFFF
#define COLOR_ERROR 0x9C0000FF
#define COLOR_SUCCESS 0x1DB954FF
#define COLOR_WARNING 0xF1C40FFF
#define COLOR_ADMIN 0xE67E22FF

#define MAX_LOGIN_ATTEMPTS 3
#define MAX_ACCOUNT_PASSWORD 64
#define MAX_ACCOUNT_SALT 24

new DB:gDatabaseHandle = DB:0;

enum E_PLAYER_DATA
{
    bool:pConnected,
    bool:pLogged,
    bool:pRegistered,
    bool:pSpawnPrepared,
    pLoginAttempts,
    pID,
    pLevel,
    pMoney,
    pSkin,
    Float:pSpawnX,
    Float:pSpawnY,
    Float:pSpawnZ,
    Float:pSpawnAngle,
    pPassword[MAX_ACCOUNT_PASSWORD + 1],
    pSalt[MAX_ACCOUNT_SALT + 1],
    pIP[16],
    pLastLogin[32],
    pSessionStart,
    pPlayTime,
    pBankBalance,
    pPaycheck,
    pJobID,
    pJobExperience,
    pPropertyID,
    bool:pPropertySpawn
};

new PlayerData[MAX_PLAYERS][E_PLAYER_DATA];

forward Core_Init();
forward Core_Shutdown();
forward Core_Log(const message[]);
forward Core_FormatTime(datetime[], length);
forward Core_ResetPlayerData(playerid);

stock Core_Init()
{
    print("[Core] Inicjalizacja podstawowych komponentow...");
    return 1;
}

stock Core_Shutdown()
{
    print("[Core] Zamkniecie podstawowych komponentow...");
    return 1;
}

stock Core_Log(const message[])
{
    new timestamp[32];
    Core_FormatTime(timestamp, sizeof(timestamp));
    printf("[%s] %s", timestamp, message);
    return 1;
}

stock Core_FormatTime(datetime[], length)
{
    new year, month, day, hour, minute, second;
    getdate(year, month, day);
    gettime(hour, minute, second);
    format(datetime, length, "%04d-%02d-%02d %02d:%02d:%02d", year, month, day, hour, minute, second);
    return 1;
}

stock Core_ResetPlayerData(playerid)
{
    PlayerData[playerid][pConnected] = false;
    PlayerData[playerid][pLogged] = false;
    PlayerData[playerid][pRegistered] = false;
    PlayerData[playerid][pSpawnPrepared] = false;
    PlayerData[playerid][pLoginAttempts] = 0;
    PlayerData[playerid][pID] = -1;
    PlayerData[playerid][pLevel] = 1;
    PlayerData[playerid][pMoney] = 0;
    PlayerData[playerid][pSkin] = 0;
    PlayerData[playerid][pSpawnX] = 1958.3783;
    PlayerData[playerid][pSpawnY] = 1343.1572;
    PlayerData[playerid][pSpawnZ] = 15.3746;
    PlayerData[playerid][pSpawnAngle] = 90.0;
    PlayerData[playerid][pPassword][0] = '\0';
    PlayerData[playerid][pSalt][0] = '\0';
    PlayerData[playerid][pIP][0] = '\0';
    PlayerData[playerid][pLastLogin][0] = '\0';
    PlayerData[playerid][pSessionStart] = 0;
    PlayerData[playerid][pPlayTime] = 0;
    PlayerData[playerid][pBankBalance] = 0;
    PlayerData[playerid][pPaycheck] = 0;
    PlayerData[playerid][pJobID] = 0;
    PlayerData[playerid][pJobExperience] = 0;
    PlayerData[playerid][pPropertyID] = 0;
    PlayerData[playerid][pPropertySpawn] = false;
    return 1;
}

