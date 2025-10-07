#if defined _ECONOMY_MODULE_INCLUDED
    #endinput
#endif
#define _ECONOMY_MODULE_INCLUDED

#define ECONOMY_PAYDAY_INTERVAL   (600000)
#define ECONOMY_BASE_SALARY       (250)
#define ECONOMY_LEVEL_BONUS       (25)
#define ECONOMY_EXPERIENCE_BONUS  (5)
#define ECONOMY_MAX_PAYCHECK      (50000)
#define ECONOMY_MAX_TRANSFER      (100000)
#define ECONOMY_MIN_TRANSFER      (100)

enum E_ECONOMY_DATA
{
    bool:eLoaded
};

new EconomyData[MAX_PLAYERS][E_ECONOMY_DATA];
new EconomyPaydayTimer = -1;

forward Economy_Init();
forward Economy_Shutdown();
forward Economy_OnAccountLoaded(playerid);
forward Economy_OnAccountRegistered(playerid);
forward Economy_OnPlayerLogin(playerid);
forward Economy_OnPlayerDisconnect(playerid);
forward Economy_OnPlayerSave(playerid);
forward Economy_OnPlayerSpawn(playerid);
forward Economy_OnPlayerCommandText(playerid, cmdtext[]);
forward Economy_AddPaycheck(playerid, amount, const reason[]);

forward Economy_PaydayTick();

stock Economy_Init()
{
    for(new i = 0; i < MAX_PLAYERS; i++)
    {
        Economy_ResetPlayer(i);
    }

    if(EconomyPaydayTimer != -1)
    {
        KillTimer(EconomyPaydayTimer);
    }

    EconomyPaydayTimer = SetTimer("Economy_PaydayTick", ECONOMY_PAYDAY_INTERVAL, true);
    Core_Log("[Economy] Zainicjalizowano modul finansowy.");
    return 1;
}

stock Economy_Shutdown()
{
    if(EconomyPaydayTimer != -1)
    {
        KillTimer(EconomyPaydayTimer);
        EconomyPaydayTimer = -1;
    }

    for(new i = 0; i < MAX_PLAYERS; i++)
    {
        if(PlayerData[i][pLogged])
        {
            Economy_SavePlayer(i);
        }
    }

    Core_Log("[Economy] Zamknieto modul finansowy.");
    return 1;
}

stock Economy_ResetPlayer(playerid)
{
    EconomyData[playerid][eLoaded] = false;
    return 1;
}

stock Economy_OnAccountLoaded(playerid)
{
    Economy_ResetPlayer(playerid);

    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query), "SELECT bank_balance, paycheck FROM account_finances WHERE account_id=%d", PlayerData[playerid][pID]);

    new DBResult:result = db_query(gDatabaseHandle, query);

    if(result && db_num_rows(result) > 0)
    {
        db_next_row(result);
        PlayerData[playerid][pBankBalance] = Database_FetchInt(result, "bank_balance");
        PlayerData[playerid][pPaycheck] = Database_FetchInt(result, "paycheck");
        EconomyData[playerid][eLoaded] = true;
    }
    else
    {
        if(result)
        {
            db_free_result(result);
        }

        format(query, sizeof(query), "INSERT INTO account_finances (account_id, bank_balance, paycheck) VALUES (%d, 0, 0)", PlayerData[playerid][pID]);
        Database_Execute(query);

        PlayerData[playerid][pBankBalance] = 0;
        PlayerData[playerid][pPaycheck] = 0;
        EconomyData[playerid][eLoaded] = true;
        return 1;
    }

    if(result)
    {
        db_free_result(result);
    }

    return 1;
}

stock Economy_OnAccountRegistered(playerid)
{
    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query), "INSERT INTO account_finances (account_id, bank_balance, paycheck) VALUES (%d, 0, 0)", PlayerData[playerid][pID]);
    Database_Execute(query);

    PlayerData[playerid][pBankBalance] = 0;
    PlayerData[playerid][pPaycheck] = 0;
    EconomyData[playerid][eLoaded] = true;
    return 1;
}

stock Economy_OnPlayerLogin(playerid)
{
    if(!EconomyData[playerid][eLoaded])
    {
        Economy_OnAccountLoaded(playerid);
    }

    new message[144];
    new buffer[32];
    Economy_FormatMoney(PlayerData[playerid][pBankBalance], buffer, sizeof(buffer));
    format(message, sizeof(message), "Saldo bankowe: %s$ | Czek oczekujacy: %d$", buffer, PlayerData[playerid][pPaycheck]);
    SendClientMessage(playerid, COLOR_INFO, message);
    SendClientMessage(playerid, COLOR_INFO, "Uzyj /saldo aby sprawdzic szczegoly bankowe.");
    return 1;
}

stock Economy_OnPlayerDisconnect(playerid)
{
    if(PlayerData[playerid][pLogged])
    {
        Economy_SavePlayer(playerid);
    }
    Economy_ResetPlayer(playerid);
    return 1;
}

stock Economy_OnPlayerSave(playerid)
{
    return Economy_SavePlayer(playerid);
}

stock Economy_SavePlayer(playerid)
{
    if(!EconomyData[playerid][eLoaded] || PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new query[256];
    format(query, sizeof(query),
        "REPLACE INTO account_finances (account_id, bank_balance, paycheck, updated_at) VALUES (%d, %d, %d, CURRENT_TIMESTAMP)",
        PlayerData[playerid][pID], PlayerData[playerid][pBankBalance], PlayerData[playerid][pPaycheck]);
    Database_Execute(query);
    return 1;
}

stock Economy_OnPlayerSpawn(playerid)
{
    if(PlayerData[playerid][pLogged])
    {
        SendClientMessage(playerid, COLOR_INFO, "Pamietaj o banku: /wplac, /wyplac, /przelej, /saldo.");
    }
    return 1;
}

stock Economy_OnPlayerCommandText(playerid, cmdtext[])
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

    if(!strcmp(command, "saldo", true))
    {
        Economy_ShowBalance(playerid);
        return 1;
    }

    if(!strcmp(command, "wplac", true))
    {
        new amount;
        if(sscanf(cmdtext[1], "s[16]i", command, amount))
        {
            SendClientMessage(playerid, COLOR_INFO, "Uzycie: /wplac [kwota]");
            return 1;
        }
        Economy_Deposit(playerid, amount);
        return 1;
    }

    if(!strcmp(command, "wyplac", true))
    {
        new amount;
        if(sscanf(cmdtext[1], "s[16]i", command, amount))
        {
            SendClientMessage(playerid, COLOR_INFO, "Uzycie: /wyplac [kwota]");
            return 1;
        }
        Economy_Withdraw(playerid, amount);
        return 1;
    }

    if(!strcmp(command, "przelej", true))
    {
        new targetid, amount;
        if(sscanf(cmdtext[1], "s[16]ii", command, targetid, amount))
        {
            SendClientMessage(playerid, COLOR_INFO, "Uzycie: /przelej [id] [kwota]");
            return 1;
        }
        Economy_Transfer(playerid, targetid, amount);
        return 1;
    }

    return 0;
}

stock Economy_ShowBalance(playerid)
{
    new balanceBuffer[32];
    Economy_FormatMoney(PlayerData[playerid][pBankBalance], balanceBuffer, sizeof(balanceBuffer));

    new message[160];
    format(message, sizeof(message), "Stan konta: %s$ | Czek: %d$", balanceBuffer, PlayerData[playerid][pPaycheck]);
    SendClientMessage(playerid, COLOR_INFO, message);
    return 1;
}

stock Economy_Deposit(playerid, amount)
{
    if(amount <= 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Kwota musi byc wieksza od zera.");
        return 0;
    }

    if(GetPlayerMoney(playerid) < amount)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie posiadasz tylu pieniedzy przy sobie.");
        return 0;
    }

    GivePlayerMoney(playerid, -amount);
    PlayerData[playerid][pBankBalance] += amount;
    Economy_AddTransaction(playerid, "DEPOSIT", amount, PlayerData[playerid][pBankBalance], "Wplata gotowki");
    Economy_SavePlayer(playerid);

    new info[144];
    format(info, sizeof(info), "Wplacono %d$ na konto bankowe.", amount);
    SendClientMessage(playerid, COLOR_SUCCESS, info);
    return 1;
}

stock Economy_Withdraw(playerid, amount)
{
    if(amount <= 0)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Kwota musi byc wieksza od zera.");
        return 0;
    }

    if(PlayerData[playerid][pBankBalance] < amount)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie posiadasz tylu srodkow w banku.");
        return 0;
    }

    PlayerData[playerid][pBankBalance] -= amount;
    GivePlayerMoney(playerid, amount);
    Economy_AddTransaction(playerid, "WITHDRAW", amount, PlayerData[playerid][pBankBalance], "Wyplata gotowki");
    Economy_SavePlayer(playerid);

    new info[144];
    format(info, sizeof(info), "Wyplacono %d$ z konta bankowego.", amount);
    SendClientMessage(playerid, COLOR_SUCCESS, info);
    return 1;
}

stock Economy_Transfer(playerid, targetid, amount)
{
    if(playerid == targetid)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie mozesz wykonac przelewu do siebie.");
        return 0;
    }

    if(!IsPlayerConnected(targetid) || !PlayerData[targetid][pLogged])
    {
        SendClientMessage(playerid, COLOR_ERROR, "Wybrany gracz nie jest dostepny.");
        return 0;
    }

    if(amount < ECONOMY_MIN_TRANSFER)
    {
        new info[144];
        format(info, sizeof(info), "Minimalny przelew to %d$.", ECONOMY_MIN_TRANSFER);
        SendClientMessage(playerid, COLOR_ERROR, info);
        return 0;
    }

    if(amount > ECONOMY_MAX_TRANSFER)
    {
        new info[144];
        format(info, sizeof(info), "Maksymalny pojedynczy przelew to %d$.", ECONOMY_MAX_TRANSFER);
        SendClientMessage(playerid, COLOR_ERROR, info);
        return 0;
    }

    if(PlayerData[playerid][pBankBalance] < amount)
    {
        SendClientMessage(playerid, COLOR_ERROR, "Nie posiadasz tylu srodkow w banku.");
        return 0;
    }

    PlayerData[playerid][pBankBalance] -= amount;
    PlayerData[targetid][pBankBalance] += amount;

    Economy_AddTransaction(playerid, "TRANSFER_OUT", amount, PlayerData[playerid][pBankBalance], "Przelew wychodzacy");
    Economy_AddTransaction(targetid, "TRANSFER_IN", amount, PlayerData[targetid][pBankBalance], "Przelew przychodzacy");

    Economy_SavePlayer(playerid);
    Economy_SavePlayer(targetid);

    new senderMessage[160];
    new receiverMessage[160];

    new targetName[MAX_PLAYER_NAME + 1];
    new senderName[MAX_PLAYER_NAME + 1];
    GetPlayerName(targetid, targetName, sizeof(targetName));
    GetPlayerName(playerid, senderName, sizeof(senderName));

    format(senderMessage, sizeof(senderMessage), "Przelano %d$ na konto gracza %s.", amount, targetName);
    SendClientMessage(playerid, COLOR_SUCCESS, senderMessage);

    format(receiverMessage, sizeof(receiverMessage), "Otrzymales przelew %d$ od %s.", amount, senderName);
    SendClientMessage(targetid, COLOR_SUCCESS, receiverMessage);
    return 1;
}

stock Economy_AddPaycheck(playerid, amount, const reason[])
{
    if(amount <= 0)
    {
        return 0;
    }

    PlayerData[playerid][pPaycheck] += amount;

    if(PlayerData[playerid][pPaycheck] > ECONOMY_MAX_PAYCHECK)
    {
        PlayerData[playerid][pPaycheck] = ECONOMY_MAX_PAYCHECK;
    }

    new message[160];
    format(message, sizeof(message), "Dodano do czeku %d$ (%s). Aktualny czek: %d$.", amount, reason, PlayerData[playerid][pPaycheck]);
    SendClientMessage(playerid, COLOR_SUCCESS, message);
    return 1;
}

stock Economy_AddTransaction(playerid, const type[], amount, newBalance, const description[])
{
    if(PlayerData[playerid][pID] <= 0)
    {
        return 0;
    }

    new escapedDescription[128];
    Database_Escape(description, escapedDescription, sizeof(escapedDescription));

    new query[320];
    format(query, sizeof(query),
        "INSERT INTO transactions (account_id, type, amount, balance_after, description) VALUES (%d, '%s', %d, %d, '%s')",
        PlayerData[playerid][pID], type, amount, newBalance, escapedDescription);
    Database_Execute(query);
    return 1;
}

stock Economy_FormatMoney(amount, output[], size)
{
    format(output, size, "%d", amount);
    return 1;
}

public Economy_PaydayTick()
{
    for(new playerid = 0; playerid < MAX_PLAYERS; playerid++)
    {
        if(!IsPlayerConnected(playerid) || !PlayerData[playerid][pLogged])
        {
            continue;
        }

        Players_UpdateSession(playerid);

        new payout = ECONOMY_BASE_SALARY + (PlayerData[playerid][pLevel] * ECONOMY_LEVEL_BONUS) + (PlayerData[playerid][pJobExperience] * ECONOMY_EXPERIENCE_BONUS) + PlayerData[playerid][pPaycheck];

        if(payout <= 0)
        {
            continue;
        }

        PlayerData[playerid][pBankBalance] += payout;
        PlayerData[playerid][pPaycheck] = 0;

        Economy_AddTransaction(playerid, "PAYDAY", payout, PlayerData[playerid][pBankBalance], "Wyplata okresowa");
        Economy_SavePlayer(playerid);

        new message[160];
        format(message, sizeof(message), "Wyplata: otrzymales %d$ (bank: %d$).", payout, PlayerData[playerid][pBankBalance]);
        SendClientMessage(playerid, COLOR_INFO, message);
    }
    return 1;
}

