#if defined _VEHICLES_MODULE_INCLUDED
    #endinput
#endif
#define _VEHICLES_MODULE_INCLUDED

#define VEHICLE_RESPAWN_CHECK_INTERVAL 60000

forward Vehicles_Init();
forward Vehicles_Shutdown();
forward Vehicles_OnPlayerCommandText(playerid, cmdtext[]);
forward Vehicles_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[]);
forward Vehicles_OnVehicleSpawn(vehicleid);
forward Vehicles_OnVehicleDeath(vehicleid, killerid);
forward Vehicles_OnPlayerEnterVehicle(playerid, vehicleid, ispassenger);
forward Vehicles_OnPlayerExitVehicle(playerid, vehicleid);
forward Vehicles_LoadFromDatabase();
forward Vehicles_Save(vehicleid);
forward Vehicles_UpdateLastDriver(vehicleid, const name[]);
forward Vehicles_Respawn(vehicleid);
forward Vehicles_PerformRespawnCheck();
forward Vehicles_StartRespawnTimer();

enum E_VEHICLE_DATA
{
    bool:vExists,
    vDBID,
    vModel,
    Float:vPosX,
    Float:vPosY,
    Float:vPosZ,
    Float:vRot,
    vColor1,
    vColor2,
    vRespawnDelay,
    vOwner[32],
    vLastDriver[MAX_PLAYER_NAME + 1],
    vLastUsed
};

new VehicleData[MAX_VEHICLES][E_VEHICLE_DATA];
new VehiclesRespawnTimer = -1;

stock Vehicles_Init()
{
    for(new i = 0; i < MAX_VEHICLES; i++)
    {
        VehicleData[i][vExists] = false;
        VehicleData[i][vDBID] = -1;
        VehicleData[i][vModel] = 0;
        VehicleData[i][vPosX] = 0.0;
        VehicleData[i][vPosY] = 0.0;
        VehicleData[i][vPosZ] = 0.0;
        VehicleData[i][vRot] = 0.0;
        VehicleData[i][vColor1] = 0;
        VehicleData[i][vColor2] = 0;
        VehicleData[i][vRespawnDelay] = 300;
        VehicleData[i][vOwner][0] = '\0';
        VehicleData[i][vLastDriver][0] = '\0';
        VehicleData[i][vLastUsed] = 0;
    }
    Vehicles_LoadFromDatabase();
    Vehicles_StartRespawnTimer();
    Core_Log("[Vehicles] Zaladowano modul pojazdow.");
    return 1;
}

stock Vehicles_Shutdown()
{
    if(VehiclesRespawnTimer != -1)
    {
        KillTimer(VehiclesRespawnTimer);
        VehiclesRespawnTimer = -1;
    }
    for(new vehicleid = 0; vehicleid < MAX_VEHICLES; vehicleid++)
    {
        if(VehicleData[vehicleid][vExists])
        {
            Vehicles_Save(vehicleid);
        }
    }
    Core_Log("[Vehicles] Zapisano dane pojazdow.");
    return 1;
}

stock Vehicles_OnPlayerCommandText(playerid, cmdtext[])
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }

    if(!strcmp(cmdtext, "/vinfo", true))
    {
        if(!IsPlayerInAnyVehicle(playerid))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Nie znajdujesz sie w zadnym pojezdzie.");
            return 1;
        }

        new vehicleid = GetPlayerVehicleID(playerid);
        if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
        {
            SendClientMessage(playerid, COLOR_ERROR, "Ten pojazd nie jest zarzadzany przez system.");
            return 1;
        }

        new message[144];
        format(message, sizeof(message), "ID DB: %d | Model: %d | Wlasciciel: %s", VehicleData[vehicleid][vDBID], VehicleData[vehicleid][vModel], VehicleData[vehicleid][vOwner]);
        SendClientMessage(playerid, COLOR_INFO, message);

        format(message, sizeof(message), "Ostatni kierowca: %s | Respawn: %d s", VehicleData[vehicleid][vLastDriver], VehicleData[vehicleid][vRespawnDelay]);
        SendClientMessage(playerid, COLOR_INFO, message);
        return 1;
    }

    if(!strcmp(cmdtext, "/vpark", true))
    {
        if(!IsPlayerInAnyVehicle(playerid))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Musisz znajdowac sie w pojezdzie jako kierowca.");
            return 1;
        }

        new vehicleid = GetPlayerVehicleID(playerid);
        if(GetPlayerState(playerid) != PLAYER_STATE_DRIVER)
        {
            SendClientMessage(playerid, COLOR_ERROR, "Nie jestes kierowca.");
            return 1;
        }

        if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
        {
            SendClientMessage(playerid, COLOR_ERROR, "Ten pojazd nie jest zarzadzany przez system.");
            return 1;
        }

        new Float:x, Float:y, Float:z, Float:angle;
        GetVehiclePos(vehicleid, x, y, z);
        GetVehicleZAngle(vehicleid, angle);

        VehicleData[vehicleid][vPosX] = x;
        VehicleData[vehicleid][vPosY] = y;
        VehicleData[vehicleid][vPosZ] = z;
        VehicleData[vehicleid][vRot] = angle;

        Vehicles_Save(vehicleid);

        SendClientMessage(playerid, COLOR_SUCCESS, "Zapisano nowa pozycje pojazdu.");
        return 1;
    }

    if(!strcmp(cmdtext, "/vrespawn", true))
    {
        if(!Admin_IsPlayerAuthorized(playerid, 2))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Brak uprawnien do respawnowania pojazdow.");
            return 1;
        }

        if(!IsPlayerInAnyVehicle(playerid))
        {
            SendClientMessage(playerid, COLOR_ERROR, "Wejdz do pojazdu aby go zrespawnowac.");
            return 1;
        }

        new vehicleid = GetPlayerVehicleID(playerid);
        if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
        {
            SendClientMessage(playerid, COLOR_ERROR, "Ten pojazd nie jest zarzadzany przez system.");
            return 1;
        }

        Vehicles_Respawn(vehicleid);
        SendClientMessage(playerid, COLOR_SUCCESS, "Pojazd zostal zrespawnowany.");
        return 1;
    }

    return 0;
}

stock Vehicles_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
    return 0;
}

stock Vehicles_OnVehicleSpawn(vehicleid)
{
    if(VehicleData[vehicleid][vExists])
    {
        SetVehiclePos(vehicleid, VehicleData[vehicleid][vPosX], VehicleData[vehicleid][vPosY], VehicleData[vehicleid][vPosZ]);
        SetVehicleZAngle(vehicleid, VehicleData[vehicleid][vRot]);
    }
    return 1;
}

stock Vehicles_OnVehicleDeath(vehicleid, killerid)
{
    if(VehicleData[vehicleid][vExists])
    {
        SetTimerEx("Vehicles_Respawn", 5000, false, "d", vehicleid);
    }
    return 1;
}

stock Vehicles_OnPlayerEnterVehicle(playerid, vehicleid, ispassenger)
{
    if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
    {
        return 0;
    }

    new name[MAX_PLAYER_NAME + 1];
    GetPlayerName(playerid, name, sizeof(name));
    Vehicles_UpdateLastDriver(vehicleid, name);

    VehicleData[vehicleid][vLastUsed] = gettime();
    return 1;
}

stock Vehicles_OnPlayerExitVehicle(playerid, vehicleid)
{
    if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
    {
        return 0;
    }
    VehicleData[vehicleid][vLastUsed] = gettime();
    return 1;
}

stock Vehicles_LoadFromDatabase()
{
    new DBResult:result = db_query(gDatabaseHandle, "SELECT * FROM vehicles");
    if(!result)
    {
        Core_Log("[Vehicles] Brak danych pojazdow w bazie.");
        return 0;
    }

    new rows = db_num_rows(result);
    if(rows == 0)
    {
        Core_Log("[Vehicles] Baza pojazdow jest pusta.");
        db_free_result(result);
        return 1;
    }

    for(new i = 0; i < rows; i++)
    {
        if(i > 0) db_next_row(result);

        new dbid = Database_FetchInt(result, "id");
        new model = Database_FetchInt(result, "model");
        new Float:x = Database_FetchFloat(result, "position_x");
        new Float:y = Database_FetchFloat(result, "position_y");
        new Float:z = Database_FetchFloat(result, "position_z");
        new Float:rot = Database_FetchFloat(result, "rotation");
        new color1 = Database_FetchInt(result, "color_1");
        new color2 = Database_FetchInt(result, "color_2");
        new respawnDelay = Database_FetchInt(result, "respawn_delay");

        new vehicleid = CreateVehicle(model, x, y, z, rot, color1, color2, respawnDelay);
        if(vehicleid == INVALID_VEHICLE_ID)
        {
            Core_Log("[Vehicles] Nie udalo sie utworzyc pojazdu z bazy.");
            continue;
        }

        VehicleData[vehicleid][vExists] = true;
        VehicleData[vehicleid][vDBID] = dbid;
        VehicleData[vehicleid][vModel] = model;
        VehicleData[vehicleid][vPosX] = x;
        VehicleData[vehicleid][vPosY] = y;
        VehicleData[vehicleid][vPosZ] = z;
        VehicleData[vehicleid][vRot] = rot;
        VehicleData[vehicleid][vColor1] = color1;
        VehicleData[vehicleid][vColor2] = color2;
        VehicleData[vehicleid][vRespawnDelay] = respawnDelay;
        Database_FetchString(result, "owner", VehicleData[vehicleid][vOwner], sizeof(VehicleData[vehicleid][vOwner]));
        Database_FetchString(result, "last_driver", VehicleData[vehicleid][vLastDriver], sizeof(VehicleData[vehicleid][vLastDriver]));
        VehicleData[vehicleid][vLastUsed] = gettime();
    }

    db_free_result(result);
    return 1;
}

stock Vehicles_Save(vehicleid)
{
    if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
    {
        return 0;
    }

    new escapedDriver[2 * (MAX_PLAYER_NAME + 1)];
    Database_Escape(VehicleData[vehicleid][vLastDriver], escapedDriver, sizeof(escapedDriver));

    new query[256];
    format(query, sizeof(query), "UPDATE vehicles SET position_x=%f, position_y=%f, position_z=%f, rotation=%f, last_driver='%s' WHERE id=%d",
        VehicleData[vehicleid][vPosX], VehicleData[vehicleid][vPosY], VehicleData[vehicleid][vPosZ], VehicleData[vehicleid][vRot], escapedDriver, VehicleData[vehicleid][vDBID]);
    Database_Execute(query);
    return 1;
}

stock Vehicles_UpdateLastDriver(vehicleid, const name[])
{
    if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
    {
        return 0;
    }
    format(VehicleData[vehicleid][vLastDriver], sizeof(VehicleData[vehicleid][vLastDriver]), "%s", name);
    Vehicles_Save(vehicleid);
    return 1;
}

public Vehicles_Respawn(vehicleid)
{
    if(vehicleid == INVALID_VEHICLE_ID || !VehicleData[vehicleid][vExists])
    {
        return 0;
    }
    SetVehicleToRespawn(vehicleid);
    SetVehiclePos(vehicleid, VehicleData[vehicleid][vPosX], VehicleData[vehicleid][vPosY], VehicleData[vehicleid][vPosZ]);
    SetVehicleZAngle(vehicleid, VehicleData[vehicleid][vRot]);
    return 1;
}

public Vehicles_PerformRespawnCheck()
{
    new current = gettime();
    for(new vehicleid = 0; vehicleid < MAX_VEHICLES; vehicleid++)
    {
        if(!VehicleData[vehicleid][vExists])
        {
            continue;
        }

        if(IsVehicleOccupied(vehicleid))
        {
            VehicleData[vehicleid][vLastUsed] = current;
            continue;
        }

        if(current - VehicleData[vehicleid][vLastUsed] >= VehicleData[vehicleid][vRespawnDelay])
        {
            Vehicles_Respawn(vehicleid);
            VehicleData[vehicleid][vLastUsed] = current;
        }
    }
    return 1;
}

stock Vehicles_StartRespawnTimer()
{
    if(VehiclesRespawnTimer != -1)
    {
        KillTimer(VehiclesRespawnTimer);
    }
    VehiclesRespawnTimer = SetTimer("Vehicles_PerformRespawnCheck", VEHICLE_RESPAWN_CHECK_INTERVAL, true);
    return 1;
}

stock bool:IsVehicleOccupied(vehicleid)
{
    for(new i = 0; i < MAX_PLAYERS; i++)
    {
        if(IsPlayerConnected(i) && GetPlayerVehicleID(i) == vehicleid)
        {
            return true;
        }
    }
    return false;
}

