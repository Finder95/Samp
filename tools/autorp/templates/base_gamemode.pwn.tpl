$metadata_banner

#include <a_samp>

#define GAMEMODE_NAME "$name"
#define GAMEMODE_AUTHOR "$author"
#define INVALID_FACTION (-1)

new const GAMEMODE_DESCRIPTION[] = "$description";

$faction_enum

$faction_definitions

$job_enum

$economy_definitions

$property_enum

$property_definitions

$property_pickup_array

$npc_enum

$npc_actor_array

new PlayerFaction[MAX_PLAYERS];
new PlayerJob[MAX_PLAYERS];

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
forward HandleJobPaycheck(playerid, salary);
forward HandlePropertyPurchase(playerid, propertyid);
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

SetupEvents()
{
$event_setup
    return 1;
}

public OnPlayerConnect(playerid)
{
    PlayerFaction[playerid] = $default_faction_constant;
    PlayerJob[playerid] = JOB_NONE;
    SendClientMessage(playerid, 0xFFFFFFFF, "$welcome_message");
    return 1;
}

public OnPlayerDisconnect(playerid, reason)
{
    PlayerFaction[playerid] = $default_faction_constant;
    PlayerJob[playerid] = JOB_NONE;
    return 1;
}

public OnPlayerPickUpPickup(playerid, pickupid)
{
$property_pickup_handlers
}

public OnPlayerCommandText(playerid, cmdtext[])
{
$command_handlers
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

$event_handlers
