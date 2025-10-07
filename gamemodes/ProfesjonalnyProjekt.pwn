#include <a_samp>
#include <sqlite>
#include <Whirlpool>
#include <sscanf2>

#include "../inc/gamemode/core.inc"
#include "../inc/gamemode/database.inc"
#include "../inc/gamemode/players.inc"
#include "../inc/gamemode/properties.inc"
#include "../inc/gamemode/economy.inc"
#include "../inc/gamemode/jobs.inc"
#include "../inc/gamemode/admin.inc"
#include "../inc/gamemode/vehicles.inc"

public OnGameModeInit()
{
    Core_Init();
    Database_Init();
    Database_CreateStructure();

    Players_Init();
    Properties_Init();
    Economy_Init();
    Jobs_Init();
    Admin_Init();
    Vehicles_Init();

    SetGameModeText(SERVER_NAME);
    ShowPlayerMarkers(PLAYER_MARKERS_MODE_GLOBAL);
    EnableStuntBonusForAll(0);
    SendRconCommand("hostname " SERVER_NAME);
    SendRconCommand("language Polski");
    Core_Log("GameMode wystartowal pomyslnie.");
    return 1;
}

public OnGameModeExit()
{
    Vehicles_Shutdown();
    Jobs_Shutdown();
    Economy_Shutdown();
    Properties_Shutdown();
    Players_Shutdown();
    Admin_Shutdown();
    Database_Shutdown();
    Core_Shutdown();
    return 1;
}

public OnPlayerConnect(playerid)
{
    return Players_OnPlayerConnect(playerid);
}

public OnPlayerDisconnect(playerid, reason)
{
    return Players_OnPlayerDisconnect(playerid, reason);
}

public OnPlayerRequestClass(playerid, classid)
{
    return Players_OnPlayerRequestClass(playerid, classid);
}

public OnPlayerSpawn(playerid)
{
    return Players_OnPlayerSpawn(playerid);
}

public OnPlayerCommandText(playerid, cmdtext[])
{
    if(Admin_OnPlayerCommandText(playerid, cmdtext))
    {
        return 1;
    }
    if(Vehicles_OnPlayerCommandText(playerid, cmdtext))
    {
        return 1;
    }
    return Players_OnPlayerCommandText(playerid, cmdtext);
}

public OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
    if(Players_OnDialogResponse(playerid, dialogid, response, listitem, inputtext))
    {
        return 1;
    }
    if(Vehicles_OnDialogResponse(playerid, dialogid, response, listitem, inputtext))
    {
        return 1;
    }
    return 0;
}

public OnPlayerStateChange(playerid, newstate, oldstate)
{
    return Players_OnPlayerStateChange(playerid, newstate, oldstate);
}

public OnVehicleSpawn(vehicleid)
{
    return Vehicles_OnVehicleSpawn(vehicleid);
}

public OnVehicleDeath(vehicleid, killerid)
{
    if(Jobs_OnVehicleDeath(vehicleid, killerid))
    {
        return 1;
    }
    return Vehicles_OnVehicleDeath(vehicleid, killerid);
}

public OnPlayerEnterVehicle(playerid, vehicleid, ispassenger)
{
    return Vehicles_OnPlayerEnterVehicle(playerid, vehicleid, ispassenger);
}

public OnPlayerExitVehicle(playerid, vehicleid)
{
    if(Jobs_OnPlayerExitVehicle(playerid, vehicleid))
    {
        return 1;
    }
    return Vehicles_OnPlayerExitVehicle(playerid, vehicleid);
}

public OnRconCommand(cmd[])
{
    return Admin_OnRconCommand(cmd);
}

public OnPlayerEnterCheckpoint(playerid)
{
    if(Jobs_OnPlayerEnterCheckpoint(playerid))
    {
        return 1;
    }
    return 0;
}

public OnPlayerPickUpPickup(playerid, pickupid)
{
    if(Properties_OnPlayerPickUpPickup(playerid, pickupid))
    {
        return 1;
    }
    if(Jobs_OnPlayerPickUpPickup(playerid, pickupid))
    {
        return 1;
    }
    return 0;
}
