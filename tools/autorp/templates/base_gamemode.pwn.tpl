$metadata_banner

#include <a_samp>

#define GAMEMODE_NAME "$name"
#define GAMEMODE_AUTHOR "$author"
#define INVALID_FACTION (-1)
#define QUEST_NONE (-1)

new const GAMEMODE_DESCRIPTION[] = "$description";

$faction_enum

$faction_definitions

$job_enum

$economy_definitions

$property_enum

$property_definitions

$property_pickup_array

$business_enum

$business_definitions

$business_pickup_array

$npc_enum

$npc_actor_array

$quest_enum

$quest_definitions

$quest_step_definitions

$quest_step_offsets

$crafting_definitions

$achievement_enum

$achievement_definitions

$weather_stage_definitions

#define QUEST_COUNT (sizeof(gQuests))
#define ACHIEVEMENT_COUNT (sizeof(gAchievements))
#define WEATHER_STAGE_COUNT (sizeof(gWeatherStages))

new PlayerFaction[MAX_PLAYERS];
new PlayerJob[MAX_PLAYERS];
new PlayerQuest[MAX_PLAYERS];
new PlayerQuestStep[MAX_PLAYERS];
new bool:PlayerAchievements[MAX_PLAYERS][ACHIEVEMENT_COUNT];

enum eItemData {
    ItemName[32],
    ItemDescription[128],
    ItemPrice,
    Float:ItemWeight
};
$item_definitions

enum eJobData {
    JobName[32],
    JobDescription[128],
    JobSalary,
    JobJoinCommand[32],
    JobRequiredFaction
};
$job_definitions

enum eJobTask {
    JobTaskDescription[128],
    JobTaskReward,
    JobTaskHint[32]
};
$job_task_definitions

forward SetupEconomy();
forward SetupItems();
forward SetupFactions();
forward SetupSpawns();
forward SetupVehicles();
forward SetupJobs();
forward SetupPickups();
forward SetupProperties();
forward SetupNpcs();
forward SetupEvents();
forward SetupQuests();
forward SetupBusinesses();
forward SetupCrafting();
forward SetupAchievements();
forward SetupWeatherCycle();
forward HandleJobPaycheck(playerid, salary);
forward HandlePropertyPurchase(playerid, propertyid);
forward HandlePropertyPickup(playerid, pickupid);
forward HandleBusinessPickup(playerid, pickupid);
forward HandleBusinessPurchase(playerid, businessid);
forward StartQuest(playerid, questid);
forward ShowQuestProgress(playerid, questid);
forward CompleteQuest(playerid, questid);
forward ApplyWeatherStage(stageIndex);
$event_forwards

public OnGameModeInit()
{
    print("[AutoRP] Ładowanie gamemodu " GAMEMODE_NAME);
    SetGameModeText(GAMEMODE_NAME);
$server_commands
$world_setup
    SetupEconomy();
    SetupItems();
    SetupFactions();
    SetupSpawns();
    SetupVehicles();
    SetupJobs();
    SetupPickups();
    SetupProperties();
    SetupNpcs();
    SetupBusinesses();
    SetupQuests();
    SetupCrafting();
    SetupAchievements();
    SetupWeatherCycle();
    SetupEvents();
    return 1;
}

public OnGameModeExit()
{
    print("[AutoRP] Zatrzymywanie gamemodu " GAMEMODE_NAME);
    return 1;
}

SetupEconomy()
{
$economy_setup
    return 1;
}

SetupItems()
{
    printf("[AutoRP] Załadowano %d pozycji ekwipunku.", sizeof(gItems));
    return 1;
}

SetupFactions()
{
$faction_setup
    return 1;
}

SetupSpawns()
{
$spawn_points
    return 1;
}

SetupVehicles()
{
$vehicle_spawns
    return 1;
}

SetupJobs()
{
    printf("[AutoRP] Dostępne prace: %d", sizeof(gJobs));
    return 1;
}

SetupPickups()
{
$pickup_setup
    return 1;
}

SetupProperties()
{
$property_setup
    return 1;
}

SetupNpcs()
{
$npc_setup
    return 1;
}

SetupBusinesses()
{
$business_setup
    return 1;
}

SetupQuests()
{
$quest_setup
    return 1;
}

SetupCrafting()
{
$crafting_setup
    return 1;
}

SetupAchievements()
{
$achievement_setup
    return 1;
}

SetupWeatherCycle()
{
$weather_setup
    return 1;
}

SetupEvents()
{
$event_setup
    return 1;
}

public OnPlayerConnect(playerid)
{
    PlayerFaction[playerid] = $default_faction_constant;
    PlayerJob[playerid] = JOB_NONE;
    PlayerQuest[playerid] = QUEST_NONE;
    PlayerQuestStep[playerid] = 0;
    for (new i = 0; i < ACHIEVEMENT_COUNT; i++)
    {
        PlayerAchievements[playerid][i] = false;
    }
    SendClientMessage(playerid, 0xFFFFFFFF, "$welcome_message");
    return 1;
}

public OnPlayerDisconnect(playerid, reason)
{
    PlayerFaction[playerid] = $default_faction_constant;
    PlayerJob[playerid] = JOB_NONE;
    PlayerQuest[playerid] = QUEST_NONE;
    PlayerQuestStep[playerid] = 0;
    for (new i = 0; i < ACHIEVEMENT_COUNT; i++)
    {
        PlayerAchievements[playerid][i] = false;
    }
    return 1;
}

public OnPlayerPickUpPickup(playerid, pickupid)
{
    if (HandlePropertyPickup(playerid, pickupid))
    {
        return 1;
    }
    if (HandleBusinessPickup(playerid, pickupid))
    {
        return 1;
    }
    return 1;
}

public OnPlayerCommandText(playerid, cmdtext[])
{
$command_handlers
}

public HandlePropertyPickup(playerid, pickupid)
{
$property_pickup_handlers
}

public HandleBusinessPickup(playerid, pickupid)
{
$business_pickup_handlers
}

public HandleJobPaycheck(playerid, salary)
{
    if(!IsPlayerConnected(playerid))
    {
        return 0;
    }
    GivePlayerMoney(playerid, salary);
    new msg[96];
    format(msg, sizeof(msg), "Otrzymujesz wypłatę %d$ za swoją pracę.", salary);
    SendClientMessage(playerid, 0x33AA33FF, msg);
    return 1;
}

public HandlePropertyPurchase(playerid, propertyid)
{
    #pragma unused propertyid
    if(!IsPlayerConnected(playerid))
    {
        return 0;
    }
    SendClientMessage(playerid, 0x33AA33FF, "System zakupu nieruchomości nie został jeszcze zaimplementowany.");
    return 1;
}

public HandleBusinessPurchase(playerid, businessid)
{
    #pragma unused businessid
    if(!IsPlayerConnected(playerid))
    {
        return 0;
    }
    SendClientMessage(playerid, 0x33AA33FF, "System zakupu biznesów wymaga implementacji po stronie serwera.");
    return 1;
}

public StartQuest(playerid, questid)
{
    if (QUEST_COUNT == 0)
    {
        return 0;
    }
    if (questid < 0 || questid >= QUEST_COUNT)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Nie odnaleziono danych questa.");
        return 0;
    }
    PlayerQuest[playerid] = questid;
    PlayerQuestStep[playerid] = 0;
    new msg[176];
    format(msg, sizeof(msg), "Rozpoczynasz quest: %s", gQuests[questid][QuestName]);
    SendClientMessage(playerid, 0x33AA33FF, msg);
    if (strlen(gQuests[questid][QuestDescription]))
    {
        SendClientMessage(playerid, 0xFFFFFFFF, gQuests[questid][QuestDescription]);
    }
    ShowQuestProgress(playerid, questid);
    return 1;
}

public ShowQuestProgress(playerid, questid)
{
    if (QUEST_COUNT == 0)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Brak aktywnych questów na serwerze.");
        return 0;
    }
    if (questid < 0 || questid >= QUEST_COUNT)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Nie odnaleziono danych questa.");
        return 0;
    }
    if (sizeof(gQuestStepOffsets) <= questid)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Ten quest nie posiada kroków.");
        return 0;
    }
    new start = gQuestStepOffsets[questid][0];
    new total = gQuestStepOffsets[questid][1];
    new header[176];
    format(header, sizeof(header), "Quest: %s", gQuests[questid][QuestName]);
    SendClientMessage(playerid, 0x88FFFFFF, header);
    if (strlen(gQuests[questid][QuestDescription]))
    {
        SendClientMessage(playerid, 0xFFFFFFFF, gQuests[questid][QuestDescription]);
    }
    if (total == 0)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Quest fabularny - brak kroków do wyświetlenia.");
        return 1;
    }
    new step = PlayerQuestStep[playerid];
    if (step >= total)
    {
        SendClientMessage(playerid, 0x55FF55FF, "Quest ukończony - użyj /questzakoncz aby odebrać nagrodę.");
        return 1;
    }
    new index = start + step;
    if (index >= sizeof(gQuestSteps))
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Brak danych kroku questa.");
        return 0;
    }
    new detail[192];
    format(detail, sizeof(detail), "Krok %d/%d: %s", step + 1, total, gQuestSteps[index][QuestStepDescription]);
    SendClientMessage(playerid, 0x88FFFFFF, detail);
    if (strlen(gQuestSteps[index][QuestStepHint]))
    {
        SendClientMessage(playerid, 0xAAAAAAFF, gQuestSteps[index][QuestStepHint]);
    }
    if (strlen(gQuestSteps[index][QuestStepGiveItem]))
    {
        new giveMsg[144];
        format(giveMsg, sizeof(giveMsg), "Nagroda pomocnicza: %s", gQuestSteps[index][QuestStepGiveItem]);
        SendClientMessage(playerid, 0x55FF55FF, giveMsg);
    }
    if (strlen(gQuestSteps[index][QuestStepTakeItem]))
    {
        new takeMsg[144];
        format(takeMsg, sizeof(takeMsg), "Oddaj przedmiot: %s", gQuestSteps[index][QuestStepTakeItem]);
        SendClientMessage(playerid, 0xFFA500FF, takeMsg);
    }
    if (gQuestSteps[index][QuestStepHasTeleport])
    {
        SetPlayerPos(playerid, gQuestSteps[index][QuestStepX], gQuestSteps[index][QuestStepY], gQuestSteps[index][QuestStepZ]);
        if (gQuestSteps[index][QuestStepInterior])
        {
            SetPlayerInterior(playerid, gQuestSteps[index][QuestStepInterior]);
        }
        if (gQuestSteps[index][QuestStepWorld])
        {
            SetPlayerVirtualWorld(playerid, gQuestSteps[index][QuestStepWorld]);
        }
    }
    return 1;
}

public CompleteQuest(playerid, questid)
{
    if (QUEST_COUNT == 0)
    {
        return 0;
    }
    if (questid < 0 || questid >= QUEST_COUNT)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Nie odnaleziono danych questa.");
        return 0;
    }
    new total = 0;
    if (sizeof(gQuestStepOffsets) > questid)
    {
        total = gQuestStepOffsets[questid][1];
    }
    PlayerQuestStep[playerid] = total;
    new msg[192];
    format(msg, sizeof(msg), "Ukończyłeś quest: %s", gQuests[questid][QuestName]);
    SendClientMessage(playerid, 0x55FF55FF, msg);
    if (gQuests[questid][QuestRewardMoney] > 0)
    {
        GivePlayerMoney(playerid, gQuests[questid][QuestRewardMoney]);
        format(msg, sizeof(msg), "Nagroda: %d$", gQuests[questid][QuestRewardMoney]);
        SendClientMessage(playerid, 0x55FF55FF, msg);
    }
    if (strlen(gQuests[questid][QuestRewardItem]))
    {
        format(msg, sizeof(msg), "Otrzymujesz przedmiot: %s", gQuests[questid][QuestRewardItem]);
        SendClientMessage(playerid, 0x55FF55FF, msg);
    }
    if (strlen(gQuests[questid][QuestCompletionMessage]))
    {
        SendClientMessage(playerid, 0xFFFFFFFF, gQuests[questid][QuestCompletionMessage]);
    }
    PlayerQuest[playerid] = QUEST_NONE;
    return 1;
}

public ApplyWeatherStage(stageIndex)
{
    if (WEATHER_STAGE_COUNT == 0)
    {
        return 0;
    }
    if (stageIndex < 0)
    {
        stageIndex = 0;
    }
    if (stageIndex >= WEATHER_STAGE_COUNT)
    {
        stageIndex = 0;
    }
    SetWorldTime(gWeatherStages[stageIndex][WeatherStageHour]);
    SetWeather(gWeatherStages[stageIndex][WeatherStageWeather]);
    if (strlen(gWeatherStages[stageIndex][WeatherStageDescription]))
    {
        new msg[160];
        format(msg, sizeof(msg), "[Pogoda] %s", gWeatherStages[stageIndex][WeatherStageDescription]);
        SendClientMessageToAll(0x6495EDFF, msg);
    }
    new duration = gWeatherStages[stageIndex][WeatherStageDurationMinutes];
    if (duration <= 0)
    {
        duration = 1;
    }
    SetTimerEx("ApplyWeatherStage", duration * 60000, false, "d", stageIndex + 1);
    return 1;
}

$event_handlers
