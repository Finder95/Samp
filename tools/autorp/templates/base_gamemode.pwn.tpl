$metadata_banner

#include <a_samp>

#define GAMEMODE_NAME "$name"
#define GAMEMODE_AUTHOR "$author"
#define INVALID_FACTION (-1)
#define QUEST_NONE (-1)
#define SKILL_NONE (-1)

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

$skill_enum

$skill_data_enum

#if SKILL_COUNT > 0
#define SKILL_MAX_LEVELS $skill_max_levels
$skill_definitions

$skill_level_requirements

$skill_reward_messages
#else
#define SKILL_MAX_LEVELS 0
// Brak umiejętności do załadowania
#endif

$skill_training_enum

#if SKILL_TRAINING_COUNT > 0
$skill_training_data_enum

$skill_training_definitions
#endif

$territory_enum

$territory_data_enum

#if TERRITORY_COUNT > 0
$territory_definitions
#endif

$weather_stage_definitions

#define QUEST_COUNT (sizeof(gQuests))
#define ACHIEVEMENT_COUNT (sizeof(gAchievements))
#define WEATHER_STAGE_COUNT (sizeof(gWeatherStages))

new PlayerFaction[MAX_PLAYERS];
new PlayerJob[MAX_PLAYERS];
new PlayerQuest[MAX_PLAYERS];
new PlayerQuestStep[MAX_PLAYERS];
new bool:PlayerAchievements[MAX_PLAYERS][ACHIEVEMENT_COUNT];
#if SKILL_COUNT > 0
new PlayerSkillLevel[MAX_PLAYERS][SKILL_COUNT];
new PlayerSkillXp[MAX_PLAYERS][SKILL_COUNT];
#endif
#if SKILL_TRAINING_COUNT > 0
new PlayerSkillTrainingCooldown[MAX_PLAYERS][SKILL_TRAINING_COUNT];
#endif
#if TERRITORY_COUNT > 0
new TerritoryOwners[TERRITORY_COUNT];
new TerritoryCaptureProgress[TERRITORY_COUNT];
new TerritoryCaptureFaction[TERRITORY_COUNT];
new TerritoryCaptureTimers[TERRITORY_COUNT];
new TerritoryCaptureStarter[TERRITORY_COUNT];
#endif

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
forward SetupSkills();
forward SetupSkillTrainings();
forward SetupWeatherCycle();
forward SetupTerritories();
forward HandleJobPaycheck(playerid, salary);
forward HandlePropertyPurchase(playerid, propertyid);
forward HandlePropertyPickup(playerid, pickupid);
forward HandleBusinessPickup(playerid, pickupid);
forward HandleBusinessPurchase(playerid, businessid);
forward HandleSkillTraining(playerid, trainingid);
forward StartQuest(playerid, questid);
forward ShowQuestProgress(playerid, questid);
forward CompleteQuest(playerid, questid);
forward ApplyWeatherStage(stageIndex);
forward StartTerritoryCapture(playerid, territoryid);
forward AdvanceTerritoryCapture(territoryid, factionid);
forward TickTerritories();
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
    SetupSkills();
    SetupSkillTrainings();
    SetupTerritories();
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

SetupSkills()
{
$skill_setup
#if SKILL_COUNT > 0
    for (new i = 0; i < SKILL_COUNT; i++)
    {
        printf("[AutoRP] Umiejętność %s dostępna z %d progami", gSkills[i][SkillName], gSkills[i][SkillLevelCount]);
    }
#endif
    return 1;
}

SetupSkillTrainings()
{
$skill_training_setup
#if SKILL_TRAINING_COUNT > 0
    for (new i = 0; i < SKILL_TRAINING_COUNT; i++)
    {
        printf("[AutoRP] Trening: %s -> %s", gSkillTrainings[i][TrainingCommand], gSkillTrainings[i][TrainingName]);
    }
#endif
    return 1;
}

SetupTerritories()
{
$territory_setup
#if TERRITORY_COUNT > 0
    for (new i = 0; i < TERRITORY_COUNT; i++)
    {
        TerritoryCaptureProgress[i] = 0;
        TerritoryCaptureFaction[i] = INVALID_FACTION;
        TerritoryCaptureTimers[i] = 0;
    }
#endif
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
#if SKILL_COUNT > 0
    for (new skill = 0; skill < SKILL_COUNT; skill++)
    {
        PlayerSkillLevel[playerid][skill] = 0;
        PlayerSkillXp[playerid][skill] = 0;
    }
#endif
#if SKILL_TRAINING_COUNT > 0
    for (new training = 0; training < SKILL_TRAINING_COUNT; training++)
    {
        PlayerSkillTrainingCooldown[playerid][training] = 0;
    }
#endif
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
#if SKILL_COUNT > 0
    for (new skill = 0; skill < SKILL_COUNT; skill++)
    {
        PlayerSkillLevel[playerid][skill] = 0;
        PlayerSkillXp[playerid][skill] = 0;
    }
#endif
#if SKILL_TRAINING_COUNT > 0
    for (new training = 0; training < SKILL_TRAINING_COUNT; training++)
    {
        PlayerSkillTrainingCooldown[playerid][training] = 0;
    }
#endif
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

public HandleSkillTraining(playerid, trainingid)
{
#if SKILL_TRAINING_COUNT == 0
    #pragma unused playerid, trainingid
    return 0;
#else
    if(!IsPlayerConnected(playerid))
    {
        return 0;
    }
    if (trainingid < 0 || trainingid >= SKILL_TRAINING_COUNT)
    {
        return 0;
    }
#if SKILL_COUNT == 0
    SendClientMessage(playerid, 0xAAAAAAFF, "Brak umiejętności skonfigurowanych na serwerze.");
    return 1;
#else
    new skillId = gSkillTrainings[trainingid][TrainingSkillId];
    if (skillId == SKILL_NONE || skillId < 0 || skillId >= SKILL_COUNT)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Ten trening nie posiada poprawnie przypisanej umiejętności.");
        return 1;
    }
    new now = GetTickCount();
    if (PlayerSkillTrainingCooldown[playerid][trainingid] > now)
    {
        new waitMs = PlayerSkillTrainingCooldown[playerid][trainingid] - now;
        new waitSec = waitMs / 1000;
        if (waitSec < 0)
        {
            waitSec = 0;
        }
        new waitMsg[144];
        format(waitMsg, sizeof(waitMsg), "Trening będzie dostępny za %d sekund.", waitSec);
        SendClientMessage(playerid, 0xAA3333FF, waitMsg);
        return 1;
    }
    new levelCount = gSkills[skillId][SkillLevelCount];
    if (levelCount <= 0)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Ta umiejętność nie posiada progów rozwoju.");
    }
    else if (PlayerSkillLevel[playerid][skillId] >= levelCount)
    {
        SendClientMessage(playerid, 0x55AAFFFF, "Umiejętność osiągnęła maksymalny poziom.");
    }
    new xpGain = gSkillTrainings[trainingid][TrainingXpGain];
    PlayerSkillXp[playerid][skillId] += xpGain;
    new info[192];
    format(info, sizeof(info), "Zdobywasz %d XP dla umiejętności %s.", xpGain, gSkills[skillId][SkillName]);
    SendClientMessage(playerid, 0x55AAFFFF, info);
    if (strlen(gSkillTrainings[trainingid][TrainingSuccessMessage]))
    {
        SendClientMessage(playerid, 0xFFFFFFFF, gSkillTrainings[trainingid][TrainingSuccessMessage]);
    }
#if SKILL_MAX_LEVELS > 0
    if (levelCount > 0 && PlayerSkillLevel[playerid][skillId] < levelCount)
    {
        new currentLevel = PlayerSkillLevel[playerid][skillId];
        if (currentLevel >= SKILL_MAX_LEVELS)
        {
            currentLevel = SKILL_MAX_LEVELS - 1;
        }
        new required = gSkillLevelXp[skillId][currentLevel];
        if (required > 0 && PlayerSkillXp[playerid][skillId] >= required)
        {
            PlayerSkillLevel[playerid][skillId] += 1;
            if (PlayerSkillLevel[playerid][skillId] > levelCount)
            {
                PlayerSkillLevel[playerid][skillId] = levelCount;
            }
            PlayerSkillXp[playerid][skillId] = 0;
            new levelMsg[192];
            format(levelMsg, sizeof(levelMsg), "Nowy poziom umiejętności %s!", gSkills[skillId][SkillName]);
            SendClientMessage(playerid, 0x88FF88FF, levelMsg);
            if (currentLevel < SKILL_MAX_LEVELS)
            {
                if (strlen(gSkillLevelMessages[skillId][currentLevel]))
                {
                    SendClientMessage(playerid, 0xFFFFFFFF, gSkillLevelMessages[skillId][currentLevel]);
                }
            }
        }
    }
#endif
    new cooldown = gSkillTrainings[trainingid][TrainingCooldown];
    if (cooldown > 0)
    {
        PlayerSkillTrainingCooldown[playerid][trainingid] = now + cooldown * 1000;
    }
    else
    {
        PlayerSkillTrainingCooldown[playerid][trainingid] = now;
    }
    return 1;
#endif
#endif
}

public StartTerritoryCapture(playerid, territoryid)
{
#if TERRITORY_COUNT == 0
    #pragma unused playerid, territoryid
    return 0;
#else
    if(!IsPlayerConnected(playerid))
    {
        return 0;
    }
    if (territoryid < 0 || territoryid >= TERRITORY_COUNT)
    {
        return 0;
    }
    new playerFaction = PlayerFaction[playerid];
    if (playerFaction == INVALID_FACTION)
    {
        SendClientMessage(playerid, 0xAA3333FF, "Przynależność frakcyjna jest wymagana do przejęcia terenu.");
        return 1;
    }
    if (TerritoryOwners[territoryid] == playerFaction)
    {
        SendClientMessage(playerid, 0xAAAAAAFF, "Twoja frakcja już kontroluje ten teren.");
        return 1;
    }
    if (TerritoryCaptureTimers[territoryid] != 0)
    {
        KillTimer(TerritoryCaptureTimers[territoryid]);
        TerritoryCaptureTimers[territoryid] = 0;
    }
    TerritoryCaptureFaction[territoryid] = playerFaction;
    TerritoryCaptureProgress[territoryid] = 0;
    TerritoryCaptureStarter[territoryid] = playerid;
    new announce[196];
    format(announce, sizeof(announce), "[Teren] %s jest przejmowany przez frakcję %d.", gTerritories[territoryid][TerritoryName], playerFaction);
    SendClientMessageToAll(0xFF9933FF, announce);
    TerritoryCaptureTimers[territoryid] = SetTimerEx("AdvanceTerritoryCapture", 1000, true, "dd", territoryid, playerFaction);
    return 1;
#endif
}

public AdvanceTerritoryCapture(territoryid, factionid)
{
#if TERRITORY_COUNT == 0
    #pragma unused territoryid, factionid
    return 0;
#else
    if (territoryid < 0 || territoryid >= TERRITORY_COUNT)
    {
        return 0;
    }
    if (TerritoryCaptureFaction[territoryid] != factionid)
    {
        return 0;
    }
    TerritoryCaptureProgress[territoryid]++;
    new captureTime = gTerritories[territoryid][TerritoryCaptureTime];
    if (captureTime <= 0)
    {
        captureTime = 30;
    }
    if (TerritoryCaptureProgress[territoryid] >= captureTime)
    {
        if (TerritoryCaptureTimers[territoryid] != 0)
        {
            KillTimer(TerritoryCaptureTimers[territoryid]);
            TerritoryCaptureTimers[territoryid] = 0;
        }
        TerritoryOwners[territoryid] = factionid;
        TerritoryCaptureFaction[territoryid] = INVALID_FACTION;
        TerritoryCaptureProgress[territoryid] = 0;
        new msg[200];
        format(msg, sizeof(msg), "[Teren] %s został przejęty przez frakcję %d!", gTerritories[territoryid][TerritoryName], factionid);
        SendClientMessageToAll(0xFFCC33FF, msg);
        if (strlen(gTerritories[territoryid][TerritoryBroadcastMessage]))
        {
            SendClientMessageToAll(0xFFCC33FF, gTerritories[territoryid][TerritoryBroadcastMessage]);
        }
        new starter = TerritoryCaptureStarter[territoryid];
        new reward = gTerritories[territoryid][TerritoryRewardMoney];
        if (reward > 0 && IsPlayerConnected(starter))
        {
            GivePlayerMoney(starter, reward);
            new rewardMsg[160];
            format(rewardMsg, sizeof(rewardMsg), "Otrzymujesz %d$ za przejęcie terenu %s.", reward, gTerritories[territoryid][TerritoryName]);
            SendClientMessage(starter, 0x88FF88FF, rewardMsg);
        }
        TerritoryCaptureStarter[territoryid] = INVALID_PLAYER_ID;
        return 1;
    }
    if ((TerritoryCaptureProgress[territoryid] % 10) == 0)
    {
        new status[180];
        format(status, sizeof(status), "[Teren] Postęp przejęcia %s: %d/%d", gTerritories[territoryid][TerritoryName], TerritoryCaptureProgress[territoryid], captureTime);
        SendClientMessageToAll(0xFF9933FF, status);
    }
    return 1;
#endif
}

public TickTerritories()
{
#if TERRITORY_COUNT == 0
    return 1;
#else
    for (new i = 0; i < TERRITORY_COUNT; i++)
    {
        if (TerritoryOwners[i] == INVALID_FACTION)
        {
            continue;
        }
        new income = gTerritories[i][TerritoryIncome];
        if (income <= 0)
        {
            continue;
        }
        new incomeMsg[192];
        format(incomeMsg, sizeof(incomeMsg), "[Teren] Frakcja %d otrzymuje %d$ za kontrolę %s.", TerritoryOwners[i], income, gTerritories[i][TerritoryName]);
        SendClientMessageToAll(0x66FF66FF, incomeMsg);
    }
    return 1;
#endif
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
