#if defined _JOBS_MODULE_INCLUDED
    #endinput
#endif
#define _JOBS_MODULE_INCLUDED

#define JOB_CENTER_X 1480.5162
#define JOB_CENTER_Y -1771.2450
#define JOB_CENTER_Z 18.7958
#define JOB_CENTER_RANGE 3.5

#define JOB_COURIER_VEHICLE_MODEL 482

#define JOB_OBJECTIVE_NONE 0
#define JOB_OBJECTIVE_COURIER_DELIVERY 1

#define DIALOG_JOB_LIST 1500
#define DIALOG_JOB_CONFIRM 1501

enum E_JOB_IDS
{
    JOB_NONE,
    JOB_COURIER,
    JOB_MECHANIC,
    JOB_COUNT
};

enum E_JOB_INFO
{
    jobName[32],
    jobDescription[144],
    jobMinLevel,
    jobBaseBonus
};

new JobInfo[JOB_COUNT][E_JOB_INFO] =
{
    {"Bezrobotny", "Brak dodatkowych benefitow.", 1, 0},
    {"Kurier", "Dostarczaj paczki do roznych czesci miasta. Kazda dostawa zwieksza twoje doswiadczenie.", 1, 350},
    {"Mechanik", "Serwisuj pojazdy graczy. Uzyj /napraw [id] aby naprawic pojazd klienta.", 2, 400}
};

enum E_JOB_RUNTIME
{
    bool:jOnDuty,
    jVehicle,
    jObjective,
    jDeliveries,
    Float:jTargetX,
    Float:jTargetY,
    Float:jTargetZ
};

new JobRuntime[MAX_PLAYERS][E_JOB_RUNTIME];
new JobDialogSelection[MAX_PLAYERS];

new gJobCenterPickup = -1;
new Text3D:gJobCenterLabel = Text3D:INVALID_3DTEXT_ID;

new Float:gCourierPoints[][3] =
{
    {2132.1470, -1151.6403, 24.0547},
    {1013.8136, -927.4852, 42.1797},
    {1588.4121, -1683.2050, 6.2188},
    {2472.3186, -1539.4280, 23.8359},
    {211.5985, -178.2676, 1.5781},
    {-2154.5969, -2460.1433, 30.6250},
    {2765.3149, 1284.5260, 10.8203}
};

forward Economy_AddPaycheck(playerid, amount, const reason[]);

forward Jobs_Init();
forward Jobs_Shutdown();
forward Jobs_OnAccountLoaded(playerid);
forward Jobs_OnAccountRegistered(playerid);
forward Jobs_OnPlayerLogin(playerid);
forward Jobs_OnPlayerDisconnect(playerid);
forward Jobs_OnPlayerSpawn(playerid);
forward Jobs_OnPlayerCommandText(playerid, cmdtext[]);
forward Jobs_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[]);
forward Jobs_OnPlayerEnterCheckpoint(playerid);
forward Jobs_OnVehicleDeath(vehicleid, killerid);
forward Jobs_OnPlayerExitVehicle(playerid, vehicleid);
forward Jobs_OnPlayerStateChange(playerid, newstate, oldstate);
forward Jobs_OnPlayerPickUpPickup(playerid, pickupid);
forward Jobs_GetJobName(jobid, output[], size);
forward Jobs_OnPlayerSave(playerid);

stock Jobs_Init()
{
    gJobCenterPickup = CreatePickup(1239, 23, JOB_CENTER_X, JOB_CENTER_Y, JOB_CENTER_Z);
    gJobCenterLabel = Create3DTextLabel("Urzad pracy\nWpisz /praca", COLOR_WHITE, JOB_CENTER_X, JOB_CENTER_Y, JOB_CENTER_Z + 1.0, 25.0, 0, 0);
    Core_Log("[Jobs] Zainicjalizowano urzad pracy.");
    return 1;
}

stock Jobs_Shutdown()
{
    if(gJobCenterPickup != -1)
    {
        DestroyPickup(gJobCenterPickup);
        gJobCenterPickup = -1;
    }

    if(gJobCenterLabel != Text3D:INVALID_3DTEXT_ID)
    {
        Delete3DTextLabel(gJobCenterLabel);
        gJobCenterLabel = Text3D:INVALID_3DTEXT_ID;
    }

    for(new i = 0; i < MAX_PLAYERS; i++)
    {
        Jobs_StopDuty(i, true);
    }

    Core_Log("[Jobs] Zamknieto modul prac.");
    return 1;
}

stock Jobs_ResetRuntime(playerid)
{
    JobRuntime[playerid][jOnDuty] = false;
    JobRuntime[playerid][jVehicle] = 0;
    JobRuntime[playerid][jObjective] = JOB_OBJECTIVE_NONE;
    JobRuntime[playerid][jDeliveries] = 0;
    JobRuntime[playerid][jTargetX] = 0.0;
    JobRuntime[playerid][jTargetY] = 0.0;
    JobRuntime[playerid][jTargetZ] = 0.0;
    JobDialogSelection[playerid] = JOB_NONE;
    return 1;
}

stock Jobs_OnAccountLoaded(playerid)
{
    Jobs_ResetRuntime(playerid);

    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query), "SELECT job_id, job_experience FROM account_jobs WHERE account_id=%d", PlayerData[playerid][pID]);

    new DBResult:result = db_query(gDatabaseHandle, query);

    if(result && db_num_rows(result) > 0)
    {
        db_next_row(result);
        PlayerData[playerid][pJobID] = Database_FetchInt(result, "job_id");
        PlayerData[playerid][pJobExperience] = Database_FetchInt(result, "job_experience");
    }
    else
    {
        if(result)
        {
            db_free_result(result);
        }

        format(query, sizeof(query), "INSERT INTO account_jobs (account_id, job_id, job_experience) VALUES (%d, %d, %d)", PlayerData[playerid][pID], JOB_NONE, 0);
        Database_Execute(query);
        PlayerData[playerid][pJobID] = JOB_NONE;
        PlayerData[playerid][pJobExperience] = 0;
        return 1;
    }

    if(result)
    {
        db_free_result(result);
    }

    return 1;
}

stock Jobs_OnAccountRegistered(playerid)
{
    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query), "INSERT INTO account_jobs (account_id, job_id, job_experience) VALUES (%d, %d, %d)", PlayerData[playerid][pID], JOB_NONE, 0);
    Database_Execute(query);
    PlayerData[playerid][pJobID] = JOB_NONE;
    PlayerData[playerid][pJobExperience] = 0;
    return 1;
}

stock Jobs_OnPlayerLogin(playerid)
{
    new jobName[32];
    Jobs_GetJobName(PlayerData[playerid][pJobID], jobName, sizeof(jobName));

    new message[160];
    format(message, sizeof(message), "Twoja praca: %s (doswiadczenie: %d).", jobName, PlayerData[playerid][pJobExperience]);
    SendClientMessage(playerid, COLOR_INFO, message);
    return 1;
}

stock Jobs_OnPlayerDisconnect(playerid)
{
    Jobs_StopDuty(playerid, true);
    return 1;
}

stock Jobs_OnPlayerSpawn(playerid)
{
    Jobs_StopDuty(playerid, false);
    return 1;
}

stock Jobs_OnPlayerSave(playerid)
{
    return Jobs_SavePlayer(playerid);
}

stock Jobs_OnPlayerCommandText(playerid, cmdtext[])
{
    if(!PlayerData[playerid][pLogged])
    {
        return 0;
    }

    new command[16];
    if(sscanf(cmdtext[1], "s[16]", command))
    {
        return 0;
    }

    if(!strcmp(command, "praca", true))
    {
        Jobs_ShowJobMenu(playerid);
        return 1;
    }

    if(!strcmp(command, "duty", true))
    {
        Jobs_StartDuty(playerid);
        return 1;
    }

    if(!strcmp(command, "koniecduty", true))
    {
        Jobs_StopDuty(playerid, false);
        SendClientMessage(playerid, COLOR_INFO, "Zakonczono dyzur.");
        return 1;
    }

    if(!strcmp(command, "napraw", true))
    {
        new targetid;
        if(sscanf(cmdtext[1], "s[16]i", command, targetid))
        {
            SendClientMessage(playerid, COLOR_INFO, "Uzycie: /napraw [id gracza]");
            return 1;
        }
        Jobs_HandleMechanicRepair(playerid, targetid);
        return 1;
    }

    return 0;
}

stock Jobs_OnDialogResponse(playerid, dialogid, response, listitem, inputtext[])
{
    switch(dialogid)
    {
        case DIALOG_JOB_LIST:
        {
            if(!response)
            {
                return 1;
            }

            if(listitem < 0 || listitem >= JOB_COUNT)
            {
                return 1;
            }

            JobDialogSelection[playerid] = listitem;
            Jobs_ShowJobConfirmation(playerid, listitem);
            return 1;
        }
        case DIALOG_JOB_CONFIRM:
        {
            if(!response)
            {
                return 1;
            }

            new jobid = JobDialogSelection[playerid];
            if(jobid < 0 || jobid >= JOB_COUNT)
            {
                return 1;
            }

            Jobs_AssignJob(playerid, jobid);
            return 1;
        }
    }
    return 0;
}

stock Jobs_OnPlayerEnterCheckpoint(playerid)
{
    if(!JobRuntime[playerid][jOnDuty])
    {
        return 0;
    }

    if(JobRuntime[playerid][jObjective] == JOB_OBJECTIVE_COURIER_DELIVERY)
    {
        if(IsPlayerInRangeOfPoint(playerid, 4.0, JobRuntime[playerid][jTargetX], JobRuntime[playerid][jTargetY], JobRuntime[playerid][jTargetZ]))
        {
            DisablePlayerCheckpoint(playerid);
            JobRuntime[playerid][jDeliveries]++;

            new payout = JobInfo[JOB_COURIER][jobBaseBonus] + (JobRuntime[playerid][jDeliveries] * 25);
            Economy_AddPaycheck(playerid, payout, "Kurier - dostawa");
            PlayerData[playerid][pJobExperience]++;
            Jobs_LogJobAction(playerid, PlayerData[playerid][pJobID], "Dostawa paczki", payout);
            Jobs_SavePlayer(playerid);
            Jobs_AssignCourierDelivery(playerid);
            return 1;
        }
    }
    return 0;
}

stock Jobs_OnVehicleDeath(vehicleid, killerid)
{
    for(new playerid = 0; playerid < MAX_PLAYERS; playerid++)
    {
        if(JobRuntime[playerid][jVehicle] == vehicleid && JobRuntime[playerid][jOnDuty])
        {
            Jobs_StopDuty(playerid, true);
            SendClientMessage(playerid, COLOR_WARNING, "Twoj pojazd sluzbowy zostal zniszczony. Dyzur zostal zakonczony.");
            return 1;
        }
    }
    return 0;
}

stock Jobs_OnPlayerExitVehicle(playerid, vehicleid)
{
    if(JobRuntime[playerid][jOnDuty] && JobRuntime[playerid][jVehicle] == vehicleid)
    {
        SendClientMessage(playerid, COLOR_WARNING, "Pozostaw pojazd sluzbowy w bezpiecznym miejscu lub zakoncz dyzur /koniecduty.");
        return 1;
    }
    return 0;
}

stock Jobs_OnPlayerStateChange(playerid, newstate, oldstate)
{
    if(newstate == PLAYER_STATE_ONFOOT && oldstate == PLAYER_STATE_DRIVER)
    {
        if(JobRuntime[playerid][jOnDuty] && JobRuntime[playerid][jVehicle] != 0)
        {
            SendClientMessage(playerid, COLOR_INFO, "Pamietaj o zabezpieczeniu pojazdu sluzbowego.");
        }
    }
    return 1;
}

stock Jobs_OnPlayerPickUpPickup(playerid, pickupid)
{
    if(pickupid == gJobCenterPickup)
    {
        Jobs_ShowJobMenu(playerid);
        return 1;
    }
    return 0;
}

stock Jobs_GetJobName(jobid, output[], size)
{
    if(jobid < 0 || jobid >= JOB_COUNT)
    {
        jobid = JOB_NONE;
    }

    format(output, size, "%s", JobInfo[jobid][jobName]);
    return 1;
}

stock Jobs_ShowJobMenu(playerid)
{
    new list[512];
    list[0] = '\0';

    for(new i = 1; i < JOB_COUNT; i++)
    {
        new line[96];
        format(line, sizeof(line), "%s\tPoziom %d\n", JobInfo[i][jobName], JobInfo[i][jobMinLevel]);
        strcat(list, line);
    }

    ShowPlayerDialog(playerid, DIALOG_JOB_LIST, DIALOG_STYLE_TABLIST_HEADERS, "Dostepne prace", list, "Wybierz", "Anuluj");
    return 1;
}

stock Jobs_ShowJobConfirmation(playerid, jobid)
{
    if(jobid < 0 || jobid >= JOB_COUNT)
    {
        return 0;
    }

    new description[256];
    format(description, sizeof(description), "%s\nWymagany poziom: %d\nPremia bazowa: %d$", JobInfo[jobid][jobDescription], JobInfo[jobid][jobMinLevel], JobInfo[jobid][jobBaseBonus]);
    ShowPlayerDialog(playerid, DIALOG_JOB_CONFIRM, DIALOG_STYLE_MSGBOX, JobInfo[jobid][jobName], description, "Potwierdz", "Wstecz");
    return 1;
}

stock Jobs_AssignJob(playerid, jobid)
{
    if(jobid < 0 || jobid >= JOB_COUNT)
    {
        return 0;
    }

    if(PlayerData[playerid][pLevel] < JobInfo[jobid][jobMinLevel])
    {
        new info[144];
        format(info, sizeof(info), "Ta praca wymaga poziomu %d.", JobInfo[jobid][jobMinLevel]);
        SendClientMessage(playerid, COLOR_ERROR, info);
        return 0;
    }

    PlayerData[playerid][pJobID] = jobid;
    PlayerData[playerid][pJobExperience] = 0;
    Jobs_SavePlayer(playerid);

    new jobName[32];
    Jobs_GetJobName(jobid, jobName, sizeof(jobName));

    new info[160];
    format(info, sizeof(info), "Twoja nowa praca to %s. Wpisz /duty aby rozpoczac dyzur.", jobName);
    SendClientMessage(playerid, COLOR_SUCCESS, info);
    return 1;
}

stock Jobs_StartDuty(playerid)
{
    if(JobRuntime[playerid][jOnDuty])
    {
        SendClientMessage(playerid, COLOR_WARNING, "Juz pelnisz dyzur.");
        return 0;
    }

    switch(PlayerData[playerid][pJobID])
    {
        case JOB_NONE:
        {
            SendClientMessage(playerid, COLOR_ERROR, "Najpierw wybierz prace w urzedzie.");
            return 0;
        }
        case JOB_COURIER:
        {
            Jobs_StartCourierDuty(playerid);
            return 1;
        }
        case JOB_MECHANIC:
        {
            Jobs_StartMechanicDuty(playerid);
            return 1;
        }
    }

    return 0;
}

stock Jobs_StopDuty(playerid, bool:force)
{
    if(!JobRuntime[playerid][jOnDuty] && !force)
    {
        return 0;
    }

    if(JobRuntime[playerid][jVehicle] != 0)
    {
        Jobs_DestroyJobVehicle(playerid);
    }

    if(JobRuntime[playerid][jObjective] != JOB_OBJECTIVE_NONE)
    {
        DisablePlayerCheckpoint(playerid);
    }

    Jobs_ResetRuntime(playerid);
    return 1;
}

stock Jobs_StartCourierDuty(playerid)
{
    Jobs_DestroyJobVehicle(playerid);

    new vehicleid = CreateVehicle(JOB_COURIER_VEHICLE_MODEL, 1475.8975, -1768.2546, 18.7958, 270.0, 3, 3, 0);
    if(vehicleid == 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie udalo sie przydzielic pojazdu sluzbowego.");
        return 0;
    }
    JobRuntime[playerid][jVehicle] = vehicleid;
    JobRuntime[playerid][jOnDuty] = true;
    JobRuntime[playerid][jObjective] = JOB_OBJECTIVE_NONE;
    JobRuntime[playerid][jDeliveries] = 0;

    if(IsPlayerConnected(playerid))
    {
        PutPlayerInVehicle(playerid, vehicleid, 0);
    }

    SendClientMessage(playerid, COLOR_INFO, "Rozpoczales dyzur kuriera. Dostarcz paczki do wskazanych punktow.");
    Jobs_AssignCourierDelivery(playerid);
    return 1;
}

stock Jobs_AssignCourierDelivery(playerid)
{
    if(!JobRuntime[playerid][jOnDuty])
    {
        return 0;
    }

    new index = random(sizeof(gCourierPoints));
    JobRuntime[playerid][jObjective] = JOB_OBJECTIVE_COURIER_DELIVERY;
    JobRuntime[playerid][jTargetX] = gCourierPoints[index][0];
    JobRuntime[playerid][jTargetY] = gCourierPoints[index][1];
    JobRuntime[playerid][jTargetZ] = gCourierPoints[index][2];

    SetPlayerCheckpoint(playerid, JobRuntime[playerid][jTargetX], JobRuntime[playerid][jTargetY], JobRuntime[playerid][jTargetZ], 3.0);

    new info[160];
    format(info, sizeof(info), "Nowa dostawa. Udaj sie do punktu %d.", index + 1);
    SendClientMessage(playerid, COLOR_INFO, info);
    return 1;
}

stock Jobs_StartMechanicDuty(playerid)
{
    JobRuntime[playerid][jOnDuty] = true;
    JobRuntime[playerid][jObjective] = JOB_OBJECTIVE_NONE;
    JobRuntime[playerid][jDeliveries] = 0;
    SendClientMessage(playerid, COLOR_INFO, "Rozpoczales dyzur mechanika. Uzyj /napraw [id] aby pomoc klientom.");
    return 1;
}

stock Jobs_HandleMechanicRepair(playerid, targetid)
{
    if(PlayerData[playerid][pJobID] != JOB_MECHANIC)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie posiadasz uprawnien mechanika.");
        return 0;
    }

    if(!JobRuntime[playerid][jOnDuty])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Musisz byc na dyzurze aby wykonywac naprawy.");
        return 0;
    }

    if(!IsPlayerConnected(targetid) || !PlayerData[targetid][pLogged])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Wybrany gracz nie jest dostepny.");
        return 0;
    }

    if(!IsPlayerInRangeOfPoint(playerid, 8.0, JOB_CENTER_X, JOB_CENTER_Y, JOB_CENTER_Z) && !IsPlayerInRangeOfPlayer(playerid, targetid, 8.0))
    {
        SendClientMessage(playerid, COLOR_WARNING, "Musisz znajdowac sie blisko klienta.");
        return 0;
    }

    if(!IsPlayerInAnyVehicle(targetid))
    {
        SendClientMessage(playerid, COLOR_ERROR, "Klient nie znajduje sie w pojezdzie.");
        return 0;
    }

    new vehicleid = GetPlayerVehicleID(targetid);
    if(vehicleid == 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie znaleziono pojazdu klienta.");
        return 0;
    }

    new Float:health;
    GetVehicleHealth(vehicleid, health);

    if(health >= 1000.0)
    {
        SendClientMessage(playerid, COLOR_WARNING, "Pojazd nie wymaga naprawy.");
        return 0;
    }

    new cost = JobInfo[JOB_MECHANIC][jobBaseBonus];

    if(GetPlayerMoney(targetid) < cost)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Klient nie posiada wystarczajacej ilosci gotowki.");
        return 0;
    }

    GivePlayerMoney(targetid, -cost);
    RepairVehicle(vehicleid);
    Economy_AddPaycheck(playerid, cost, "Mechanik - naprawa");
    PlayerData[playerid][pJobExperience] += 2;
    Jobs_LogJobAction(playerid, PlayerData[playerid][pJobID], "Naprawa pojazdu", cost);
    Jobs_SavePlayer(playerid);

    new clientName[MAX_PLAYER_NAME + 1];
    new mechanicName[MAX_PLAYER_NAME + 1];
    GetPlayerName(targetid, clientName, sizeof(clientName));
    GetPlayerName(playerid, mechanicName, sizeof(mechanicName));

    new info[160];
    format(info, sizeof(info), "Naprawiles pojazd gracza %s i otrzymales %d$ do czeku.", clientName, cost);
    SendClientMessage(playerid, COLOR_SUCCESS, info);

    format(info, sizeof(info), "Mechanik %s naprawil twoj pojazd za %d$.", mechanicName, cost);
    SendClientMessage(targetid, COLOR_INFO, info);
    return 1;
}

stock Jobs_SavePlayer(playerid)
{
    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query),
        "REPLACE INTO account_jobs (account_id, job_id, job_experience, updated_at) VALUES (%d, %d, %d, CURRENT_TIMESTAMP)",
        PlayerData[playerid][pID], PlayerData[playerid][pJobID], PlayerData[playerid][pJobExperience]);
    Database_Execute(query);
    return 1;
}

stock Jobs_DestroyJobVehicle(playerid)
{
    if(JobRuntime[playerid][jVehicle] != 0)
    {
        DestroyVehicle(JobRuntime[playerid][jVehicle]);
        JobRuntime[playerid][jVehicle] = 0;
    }
    return 1;
}

stock Jobs_LogJobAction(playerid, jobid, const action[], payout)
{
    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new escapedAction[128];
    Database_Escape(action, escapedAction, sizeof(escapedAction));

    new query[256];
    format(query, sizeof(query),
        "INSERT INTO job_logs (account_id, job_id, action, payout) VALUES (%d, %d, '%s', %d)",
        PlayerData[playerid][pID], jobid, escapedAction, payout);
    Database_Execute(query);
    return 1;
}

stock bool:IsPlayerInRangeOfPlayer(playerid, targetid, Float:range)
{
    new Float:x1, Float:y1, Float:z1;
    new Float:x2, Float:y2, Float:z2;
    GetPlayerPos(playerid, x1, y1, z1);
    GetPlayerPos(targetid, x2, y2, z2);
    return floatsqroot((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2) + (z1 - z2) * (z1 - z2)) <= range;
}

