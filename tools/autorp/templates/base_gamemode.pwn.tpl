$metadata_banner

#include <a_samp>

#define GAMEMODE_NAME "$name"
#define GAMEMODE_AUTHOR "$author"
#define INVALID_FACTION (-1)
#define QUEST_NONE (-1)
#define SKILL_NONE (-1)
#define INVALID_ROUTE (-1)
#define INVALID_HEIST (-1)
#define INVALID_TIMER (-1)
#define LAW_VIOLATION_COUNT $law_violation_count
#define PATROL_ROUTE_COUNT $patrol_route_count
#define HEIST_COUNT $heist_count

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

$law_violation_definitions

$patrol_route_definitions

$patrol_point_definitions

$heist_definitions

$heist_stage_definitions

$weather_stage_definitions

#define QUEST_COUNT (sizeof(gQuests))
#define ACHIEVEMENT_COUNT (sizeof(gAchievements))
#define WEATHER_STAGE_COUNT (sizeof(gWeatherStages))

new PlayerFaction[MAX_PLAYERS];
new PlayerJob[MAX_PLAYERS];
new PlayerQuest[MAX_PLAYERS];
new PlayerQuestStep[MAX_PLAYERS];
new bool:PlayerAchievements[MAX_PLAYERS][ACHIEVEMENT_COUNT];
new PlayerWantedLevel[MAX_PLAYERS];
new PlayerCrimePoints[MAX_PLAYERS];
#if LAW_VIOLATION_COUNT > 0
new PlayerLastViolation[MAX_PLAYERS];
#endif
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
#if PATROL_ROUTE_COUNT > 0
new PlayerActivePatrol[MAX_PLAYERS];
new PlayerPatrolPoint[MAX_PLAYERS];
new PlayerPatrolTimer[MAX_PLAYERS];
#endif
#if HEIST_COUNT > 0
new PlayerActiveHeist[MAX_PLAYERS];
new PlayerHeistStage[MAX_PLAYERS];
new PlayerHeistTimer[MAX_PLAYERS];
new HeistCooldowns[HEIST_COUNT];
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
forward SetupLaw();
forward SetupPatrols();
forward SetupHeists();
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
forward ShowPlayerLawBook(playerid);
forward ShowPlayerWantedLevel(playerid);
forward StartPatrol(playerid, routeid, factionid);
forward AdvancePatrol(playerid);
forward StopPlayerPatrol(playerid);
forward StartHeist(playerid, heistid, factionid);
forward AdvanceHeistStage(playerid);
forward CompleteHeist(playerid);
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
    SetupLaw();
    SetupPatrols();
    SetupHeists();
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

SetupLaw()
{
$law_setup
#if LAW_VIOLATION_COUNT > 0
    for (new i = 0; i < MAX_PLAYERS; i++)
    {
        PlayerLastViolation[i] = -1;
    }
#endif
    return 1;
}

SetupPatrols()
{
$patrol_setup
#if PATROL_ROUTE_COUNT > 0
    for (new i = 0; i < MAX_PLAYERS; i++)
    {
        PlayerActivePatrol[i] = INVALID_ROUTE;
        PlayerPatrolPoint[i] = 0;
        PlayerPatrolTimer[i] = INVALID_TIMER;
    }
#endif
    return 1;
}

SetupHeists()
{
$heist_setup
#if HEIST_COUNT > 0
    for (new i = 0; i < MAX_PLAYERS; i++)
    {
        PlayerActiveHeist[i] = INVALID_HEIST;
        PlayerHeistStage[i] = 0;
        PlayerHeistTimer[i] = INVALID_TIMER;
    }
    for (new h = 0; h < HEIST_COUNT; h++)
    {
        HeistCooldowns[h] = 0;
    }
#endif
    return 1;
}

stock ResetPatrolState(playerid, bool:notify)
{
#if PATROL_ROUTE_COUNT > 0
    if (PlayerPatrolTimer[playerid] != INVALID_TIMER)
    {
        KillTimer(PlayerPatrolTimer[playerid]);
        PlayerPatrolTimer[playerid] = INVALID_TIMER;
    }
    if (PlayerActivePatrol[playerid] != INVALID_ROUTE)
    {
        DisablePlayerCheckpoint(playerid);
        if (notify)
        {
            new msg[144];
            format(msg, sizeof(msg), "[Patrol] Trasa %s zakończona.", gPatrolRoutes[PlayerActivePatrol[playerid]][PatrolRouteName]);
            SendClientMessage(playerid, 0x4CAF50FF, msg);
        }
    }
    PlayerActivePatrol[playerid] = INVALID_ROUTE;
    PlayerPatrolPoint[playerid] = 0;
#else
    notify = notify;
#endif
}

stock ApplyNextPatrolPoint(playerid)
{
#if PATROL_ROUTE_COUNT > 0
    new route = PlayerActivePatrol[playerid];
    if (route == INVALID_ROUTE)
    {
        return 0;
    }
    new total = gPatrolRoutes[route][PatrolRoutePointCount];
    if (total <= 0)
    {
        ResetPatrolState(playerid, true);
        return 1;
    }
    new index = PlayerPatrolPoint[playerid];
    if (index >= total)
    {
        if (gPatrolRoutes[route][PatrolRouteLoop])
        {
            PlayerPatrolPoint[playerid] = 0;
            index = 0;
        }
        else
        {
            ResetPatrolState(playerid, true);
            return 1;
        }
    }
    new pointIndex = gPatrolRoutes[route][PatrolRoutePointStart] + index;
    new Float:px = gPatrolRoutePoints[pointIndex][PatrolPointX];
    new Float:py = gPatrolRoutePoints[pointIndex][PatrolPointY];
    new Float:pz = gPatrolRoutePoints[pointIndex][PatrolPointZ];
    SetPlayerCheckpoint(playerid, px, py, pz, 4.0);
    new waitTime = floatround(gPatrolRoutePoints[pointIndex][PatrolPointWait]);
    if (waitTime <= 0)
    {
        waitTime = 10;
    }
    if (PlayerPatrolTimer[playerid] != INVALID_TIMER)
    {
        KillTimer(PlayerPatrolTimer[playerid]);
    }
    PlayerPatrolTimer[playerid] = SetTimerEx("AdvancePatrol", waitTime * 1000, false, "d", playerid);
    PlayerPatrolPoint[playerid] = index + 1;
#else
    playerid = playerid;
#endif
    return 1;
}

public StartPatrol(playerid, routeid, factionid)
{
#if PATROL_ROUTE_COUNT > 0
    if (routeid < 0 || routeid >= PATROL_ROUTE_COUNT)
    {
        SendClientMessage(playerid, 0xAA3333FF, "[Patrol] Nieprawidłowa trasa.");
        return 1;
    }
    if (factionid != INVALID_FACTION && PlayerFaction[playerid] != factionid)
    {
        SendClientMessage(playerid, 0xAA3333FF, "[Patrol] Brak uprawnień do tej trasy.");
        return 1;
    }
    ResetPatrolState(playerid, false);
    PlayerActivePatrol[playerid] = routeid;
    PlayerPatrolPoint[playerid] = 0;
    new message[160];
    format(message, sizeof(message), "[Patrol] Rozpoczynasz trasę %s.", gPatrolRoutes[routeid][PatrolRouteName]);
    SendClientMessage(playerid, 0x4CAF50FF, message);
    if (strlen(gPatrolRoutes[routeid][PatrolRouteRadio]) > 0)
    {
        SendClientMessage(playerid, 0x4CAF50FF, gPatrolRoutes[routeid][PatrolRouteRadio]);
    }
    ApplyNextPatrolPoint(playerid);
#else
    playerid = playerid;
    routeid = routeid;
    factionid = factionid;
    SendClientMessage(playerid, 0xAA3333FF, "[Patrol] System patroli jest niedostępny.");
#endif
    return 1;
}

public AdvancePatrol(playerid)
{
#if PATROL_ROUTE_COUNT > 0
    PlayerPatrolTimer[playerid] = INVALID_TIMER;
    ApplyNextPatrolPoint(playerid);
#else
    playerid = playerid;
#endif
    return 1;
}

public StopPlayerPatrol(playerid)
{
#if PATROL_ROUTE_COUNT > 0
    if (PlayerActivePatrol[playerid] == INVALID_ROUTE)
    {
        SendClientMessage(playerid, 0x4CAF50FF, "[Patrol] Nie masz aktywnej trasy.");
        return 1;
    }
    ResetPatrolState(playerid, true);
#else
    playerid = playerid;
#endif
    return 1;
}

stock ResetHeistState(playerid, bool:notify)
{
#if HEIST_COUNT > 0
    if (PlayerHeistTimer[playerid] != INVALID_TIMER)
    {
        KillTimer(PlayerHeistTimer[playerid]);
        PlayerHeistTimer[playerid] = INVALID_TIMER;
    }
    if (notify && PlayerActiveHeist[playerid] != INVALID_HEIST)
    {
        new msg[160];
        format(msg, sizeof(msg), "[Heist] Napad %s został przerwany.", gHeists[PlayerActiveHeist[playerid]][HeistName]);
        SendClientMessage(playerid, 0xFF7043FF, msg);
    }
    PlayerActiveHeist[playerid] = INVALID_HEIST;
    PlayerHeistStage[playerid] = 0;
#else
    notify = notify;
#endif
}

stock BeginHeistStage(playerid)
{
#if HEIST_COUNT > 0
    new heistid = PlayerActiveHeist[playerid];
    if (heistid == INVALID_HEIST)
    {
        return 0;
    }
    new stageCount = gHeists[heistid][HeistStageCount];
    if (stageCount <= 0)
    {
        CompleteHeist(playerid);
        return 1;
    }
    new stageIndex = PlayerHeistStage[playerid];
    if (stageIndex >= stageCount)
    {
        CompleteHeist(playerid);
        return 1;
    }
    new stageData = gHeists[heistid][HeistStageStart] + stageIndex;
    new message[180];
    format(message, sizeof(message), "[Heist] Etap %d/%d: %s", stageIndex + 1, stageCount, gHeistStages[stageData][HeistStageDescription]);
    SendClientMessage(playerid, 0xFF7043FF, message);
    new timeLimit = gHeistStages[stageData][HeistStageTimeLimit];
    if (timeLimit <= 0)
    {
        timeLimit = 30;
    }
    if (PlayerHeistTimer[playerid] != INVALID_TIMER)
    {
        KillTimer(PlayerHeistTimer[playerid]);
    }
    PlayerHeistTimer[playerid] = SetTimerEx("AdvanceHeistStage", timeLimit * 1000, false, "d", playerid);
#else
    playerid = playerid;
#endif
    return 1;
}

public StartHeist(playerid, heistid, factionid)
{
#if HEIST_COUNT > 0
    if (heistid < 0 || heistid >= HEIST_COUNT)
    {
        SendClientMessage(playerid, 0xFF7043FF, "[Heist] Nieprawidłowy scenariusz.");
        return 1;
    }
    if (factionid != INVALID_FACTION && PlayerFaction[playerid] != factionid)
    {
        SendClientMessage(playerid, 0xFF7043FF, "[Heist] Brak uprawnień do tego napadu.");
        return 1;
    }
    if (PlayerActiveHeist[playerid] != INVALID_HEIST)
    {
        SendClientMessage(playerid, 0xFF7043FF, "[Heist] Już bierzesz udział w napadzie.");
        return 1;
    }
    new now = GetTickCount();
    if (HeistCooldowns[heistid] > now)
    {
        new remaining = HeistCooldowns[heistid] - now;
        new cooldownMsg[128];
        format(cooldownMsg, sizeof(cooldownMsg), "[Heist] Scenariusz dostępny za %d sekund.", remaining / 1000);
        SendClientMessage(playerid, 0xFF7043FF, cooldownMsg);
        return 1;
    }
    new participants = CountFactionMembers(PlayerFaction[playerid]);
    if (participants < gHeists[heistid][HeistRequiredPlayers])
    {
        new needMsg[128];
        format(needMsg, sizeof(needMsg), "[Heist] Wymagana liczba funkcjonariuszy: %d", gHeists[heistid][HeistRequiredPlayers]);
        SendClientMessage(playerid, 0xFF7043FF, needMsg);
        return 1;
    }
    ResetHeistState(playerid, false);
    PlayerActiveHeist[playerid] = heistid;
    PlayerHeistStage[playerid] = 0;
    new announce[180];
    if (strlen(gHeists[heistid][HeistAnnouncement]) > 0)
    {
        format(announce, sizeof(announce), "[Heist] %s", gHeists[heistid][HeistAnnouncement]);
        SendClientMessageToAll(0xFF7043FF, announce);
    }
    format(announce, sizeof(announce), "[Heist] Cel: %s", gHeists[heistid][HeistLocation]);
    SendClientMessage(playerid, 0xFF7043FF, announce);
    if (strlen(gHeists[heistid][HeistRequiredItems]) > 0)
    {
        format(announce, sizeof(announce), "[Heist] Wymagane przedmioty: %s", gHeists[heistid][HeistRequiredItems]);
        SendClientMessage(playerid, 0xFF7043FF, announce);
    }
#if LAW_VIOLATION_COUNT > 0
    FlagPlayerWithViolation(playerid, 0);
#endif
    BeginHeistStage(playerid);
#else
    playerid = playerid;
    heistid = heistid;
    factionid = factionid;
    SendClientMessage(playerid, 0xFF7043FF, "[Heist] System napadów jest wyłączony.");
#endif
    return 1;
}

public AdvanceHeistStage(playerid)
{
#if HEIST_COUNT > 0
    if (!IsPlayerConnected(playerid))
    {
        return 0;
    }
    PlayerHeistTimer[playerid] = INVALID_TIMER;
    new heistid = PlayerActiveHeist[playerid];
    if (heistid == INVALID_HEIST)
    {
        return 1;
    }
    new stageIndex = PlayerHeistStage[playerid];
    new stageStart = gHeists[heistid][HeistStageStart];
    new stageCount = gHeists[heistid][HeistStageCount];
    if (stageIndex < stageCount)
    {
        new stageData = stageStart + stageIndex;
        if (strlen(gHeistStages[stageData][HeistStageSuccessMessage]) > 0)
        {
            SendClientMessage(playerid, 0xFF7043FF, gHeistStages[stageData][HeistStageSuccessMessage]);
        }
    }
    PlayerHeistStage[playerid] = stageIndex + 1;
    BeginHeistStage(playerid);
#else
    playerid = playerid;
#endif
    return 1;
}

public CompleteHeist(playerid)
{
#if HEIST_COUNT > 0
    if (PlayerActiveHeist[playerid] == INVALID_HEIST)
    {
        return 1;
    }
    new heistid = PlayerActiveHeist[playerid];
    new reward = gHeists[heistid][HeistRewardMoney];
    if (reward > 0)
    {
        GivePlayerMoney(playerid, reward);
        new rewardMsg[140];
        format(rewardMsg, sizeof(rewardMsg), "[Heist] Otrzymujesz %d$ za sukces.", reward);
        SendClientMessage(playerid, 0x33AA33FF, rewardMsg);
    }
    if (strlen(gHeists[heistid][HeistRewardItem]) > 0)
    {
        new itemMsg[160];
        format(itemMsg, sizeof(itemMsg), "[Heist] Przyznano nagrodę: %s.", gHeists[heistid][HeistRewardItem]);
        SendClientMessage(playerid, 0x33AA33FF, itemMsg);
    }
    if (gHeists[heistid][HeistRewardReputation] > 0)
    {
        PlayerCrimePoints[playerid] -= gHeists[heistid][HeistRewardReputation];
        if (PlayerCrimePoints[playerid] < 0)
        {
            PlayerCrimePoints[playerid] = 0;
        }
        if (PlayerWantedLevel[playerid] > 0)
        {
            PlayerWantedLevel[playerid] -= 1;
            if (PlayerWantedLevel[playerid] < 0)
            {
                PlayerWantedLevel[playerid] = 0;
            }
        }
    }
    new announce[180];
    new playerName[MAX_PLAYER_NAME];
    GetPlayerName(playerid, playerName, sizeof(playerName));
    format(announce, sizeof(announce), "[Heist] %s ukończył scenariusz %s!", playerName, gHeists[heistid][HeistName]);
    SendClientMessageToAll(0x33AA33FF, announce);
    HeistCooldowns[heistid] = GetTickCount() + gHeists[heistid][HeistCooldownMinutes] * 60000;
    ResetHeistState(playerid, false);
#else
    playerid = playerid;
#endif
    return 1;
}

stock CountFactionMembers(factionid)
{
    new count = 0;
    for (new i = 0; i < MAX_PLAYERS; i++)
    {
        if (!IsPlayerConnected(i))
        {
            continue;
        }
        if (factionid == INVALID_FACTION || PlayerFaction[i] == factionid)
        {
            count++;
        }
    }
    return count;
}

public ShowPlayerLawBook(playerid)
{
#if LAW_VIOLATION_COUNT > 0
    SendClientMessage(playerid, 0xFFC107FF, "[Prawo] Katalog wykroczeń:");
    for (new i = 0; i < LAW_VIOLATION_COUNT; i++)
    {
        new line[200];
        format(line, sizeof(line), "%s (%s) | Grzywna: %d$ | Więzienie: %d min | Punkty: %d", gLawViolations[i][LawName], gLawViolations[i][LawCode], gLawViolations[i][LawFine], gLawViolations[i][LawJailMinutes], gLawViolations[i][LawReputationPenalty]);
        SendClientMessage(playerid, 0xFFFFFFFF, line);
    }
#else
    SendClientMessage(playerid, 0xFFC107FF, "[Prawo] Brak zdefiniowanych wykroczeń.");
#endif
    return 1;
}

public ShowPlayerWantedLevel(playerid)
{
    new line[160];
    format(line, sizeof(line), "[Prawo] Poziom poszukiwania: %d | Punkty przestępstw: %d", PlayerWantedLevel[playerid], PlayerCrimePoints[playerid]);
    SendClientMessage(playerid, 0xAA3333FF, line);
#if LAW_VIOLATION_COUNT > 0
    if (PlayerLastViolation[playerid] >= 0 && PlayerLastViolation[playerid] < LAW_VIOLATION_COUNT)
    {
        format(line, sizeof(line), "[Prawo] Ostatnie przewinienie: %s (%s)", gLawViolations[PlayerLastViolation[playerid]][LawName], gLawViolations[PlayerLastViolation[playerid]][LawCode]);
        SendClientMessage(playerid, 0xAA3333FF, line);
    }
#endif
    return 1;
}

stock FlagPlayerWithViolation(playerid, violationid)
{
#if LAW_VIOLATION_COUNT > 0
    if (violationid < 0 || violationid >= LAW_VIOLATION_COUNT)
    {
        return 0;
    }
    PlayerWantedLevel[playerid] += gLawViolations[violationid][LawSeverity];
    PlayerCrimePoints[playerid] += gLawViolations[violationid][LawReputationPenalty];
    PlayerLastViolation[playerid] = violationid;
    new message[180];
    format(message, sizeof(message), "[Prawo] Popełniasz przestępstwo: %s (kod %s).", gLawViolations[violationid][LawName], gLawViolations[violationid][LawCode]);
    SendClientMessage(playerid, 0xAA3333FF, message);
    if (gLawViolations[violationid][LawFine] > 0 || gLawViolations[violationid][LawJailMinutes] > 0)
    {
        format(message, sizeof(message), "[Prawo] Sankcje: %d$ grzywny, %d min więzienia.", gLawViolations[violationid][LawFine], gLawViolations[violationid][LawJailMinutes]);
        SendClientMessage(playerid, 0xAA3333FF, message);
    }
#else
    playerid = playerid;
    violationid = violationid;
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
    PlayerWantedLevel[playerid] = 0;
    PlayerCrimePoints[playerid] = 0;
#if LAW_VIOLATION_COUNT > 0
    PlayerLastViolation[playerid] = -1;
#endif
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
#if PATROL_ROUTE_COUNT > 0
    PlayerActivePatrol[playerid] = INVALID_ROUTE;
    PlayerPatrolPoint[playerid] = 0;
    PlayerPatrolTimer[playerid] = INVALID_TIMER;
#endif
#if HEIST_COUNT > 0
    PlayerActiveHeist[playerid] = INVALID_HEIST;
    PlayerHeistStage[playerid] = 0;
    PlayerHeistTimer[playerid] = INVALID_TIMER;
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
    PlayerWantedLevel[playerid] = 0;
    PlayerCrimePoints[playerid] = 0;
#if LAW_VIOLATION_COUNT > 0
    PlayerLastViolation[playerid] = -1;
#endif
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
#if PATROL_ROUTE_COUNT > 0
    ResetPatrolState(playerid, false);
#endif
#if HEIST_COUNT > 0
    ResetHeistState(playerid, false);
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
