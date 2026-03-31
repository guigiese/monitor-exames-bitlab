param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectKey,

    [string]$AuthPath = "$env:USERPROFILE\.codex\jira-auth.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-JiraHeaders {
    if (-not (Test-Path -LiteralPath $AuthPath)) {
        throw "Auth file not found at $AuthPath"
    }

    $auth = Get-Content -LiteralPath $AuthPath | ConvertFrom-Json
    $pair = "{0}:{1}" -f $auth.username, $auth.api_token
    $basic = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pair))

    return @{
        Authorization = "Basic $basic"
        Accept        = "application/json"
    }
}

function Invoke-JiraJson {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [object]$Body
    )

    $headers = Get-JiraHeaders
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }

    $json = $Body | ConvertTo-Json -Depth 12 -Compress
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($json))
}

function Find-FirstStatusByNames {
    param(
        [Parameter(Mandatory = $true)][object[]]$Statuses,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    foreach ($name in $Names) {
        $match = $Statuses | Where-Object { $_.name -eq $name } | Select-Object -First 1
        if ($null -ne $match) {
            return $match
        }
    }

    return $null
}

function Update-Status {
    param(
        [Parameter(Mandatory = $true)][string]$StatusId,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Category,
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )

    Invoke-JiraJson -Method "PUT" -Uri "$BaseUrl/rest/api/3/statuses" -Body @{
        statuses = @(
            @{
                id             = $StatusId
                name           = $Name
                statusCategory = $Category
                description    = $Description
            }
        )
    } | Out-Null
}

function Create-ProjectStatus {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Category,
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )

    return Invoke-JiraJson -Method "POST" -Uri "$BaseUrl/rest/api/3/statuses" -Body @{
        scope = @{
            type    = "PROJECT"
            project = @{ id = $ProjectId }
        }
        statuses = @(
            @{
                name           = $Name
                statusCategory = $Category
                description    = $Description
            }
        )
    }
}

function Ensure-ProjectStatuses {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )

    $search = Invoke-JiraJson -Method "GET" -Uri "$BaseUrl/rest/api/3/statuses/search?projectId=$ProjectId"
    $statuses = @($search.values)

    $backlog = Find-FirstStatusByNames -Statuses $statuses -Names @("Backlog", "To Do", "Tarefas pendentes", "A fazer")
    if ($null -eq $backlog) {
        $backlog = ($statuses | Where-Object { $_.statusCategory -eq "TODO" } | Select-Object -First 1)
    }
    if ($null -eq $backlog) {
        throw "Could not find a TODO status to convert into Backlog for project $ProjectId"
    }
    if ($backlog.name -ne "Backlog") {
        Update-Status -StatusId $backlog.id -Name "Backlog" -Category "TODO" -Description "Item ainda nao iniciado e sem refinamento suficiente para execucao." -BaseUrl $BaseUrl
        $backlog.name = "Backlog"
    }

    $progress = Find-FirstStatusByNames -Statuses $statuses -Names @("Em andamento", "In Progress")
    if ($null -eq $progress) {
        $progress = ($statuses | Where-Object { $_.statusCategory -eq "IN_PROGRESS" -and $_.name -notin @("Em revisão") } | Select-Object -First 1)
    }
    if ($null -eq $progress) {
        throw "Could not find an IN_PROGRESS status to convert into Em andamento for project $ProjectId"
    }
    if ($progress.name -ne "Em andamento") {
        Update-Status -StatusId $progress.id -Name "Em andamento" -Category "IN_PROGRESS" -Description "Item em execucao ativa." -BaseUrl $BaseUrl
        $progress.name = "Em andamento"
    }

    $done = Find-FirstStatusByNames -Statuses $statuses -Names @("Concluído", "Done")
    if ($null -eq $done) {
        $done = ($statuses | Where-Object { $_.statusCategory -eq "DONE" } | Select-Object -First 1)
    }
    if ($null -eq $done) {
        throw "Could not find a DONE status to convert into Concluído for project $ProjectId"
    }
    if ($done.name -ne "Concluído") {
        Update-Status -StatusId $done.id -Name "Concluído" -Category "DONE" -Description "Item concluido conforme definicao de pronto." -BaseUrl $BaseUrl
        $done.name = "Concluído"
    }

    $statuses = @( (Invoke-JiraJson -Method "GET" -Uri "$BaseUrl/rest/api/3/statuses/search?projectId=$ProjectId").values )

    $discovery = Find-FirstStatusByNames -Statuses $statuses -Names @("Descoberta")
    if ($null -eq $discovery) {
        $discovery = Create-ProjectStatus -ProjectId $ProjectId -Name "Descoberta" -Category "TODO" -Description "Item em entendimento, recorte ou validacao de abordagem." -BaseUrl $BaseUrl
    }

    $ready = Find-FirstStatusByNames -Statuses $statuses -Names @("Pronto pra dev", "Pronto")
    if ($null -eq $ready) {
        $ready = Create-ProjectStatus -ProjectId $ProjectId -Name "Pronto pra dev" -Category "TODO" -Description "Item refinado e pronto para desenvolvimento." -BaseUrl $BaseUrl
    } elseif ($ready.name -ne "Pronto pra dev") {
        Update-Status -StatusId $ready.id -Name "Pronto pra dev" -Category "TODO" -Description "Item refinado e pronto para desenvolvimento." -BaseUrl $BaseUrl
        $ready.name = "Pronto pra dev"
    }

    $review = Find-FirstStatusByNames -Statuses $statuses -Names @("Em revisão")
    if ($null -eq $review) {
        $review = Create-ProjectStatus -ProjectId $ProjectId -Name "Em revisão" -Category "IN_PROGRESS" -Description "Item em revisao funcional, tecnica ou validacao final." -BaseUrl $BaseUrl
    }

    return @{
        backlog  = $backlog.id
        discovery = $discovery.id
        ready    = $ready.id
        progress = $progress.id
        review   = $review.id
        done     = $done.id
    }
}

function Get-ProjectWorkflow {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )

    $resp = Invoke-JiraJson -Method "GET" -Uri "$BaseUrl/rest/api/3/workflows/search?expand=usage,values.transitions"
    $workflow = $resp.values | Where-Object { $_.scope.type -eq "PROJECT" -and $_.scope.project.id -eq $ProjectId } | Select-Object -First 1

    if ($null -eq $workflow) {
        throw "Could not find editable project workflow for project $ProjectId"
    }

    return $workflow
}

function Publish-StandardWorkflow {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][object]$Workflow,
        [Parameter(Mandatory = $true)][hashtable]$StatusIds
    )

    $refs = @{
        discovery = [guid]::NewGuid().ToString()
        ready     = [guid]::NewGuid().ToString()
        review    = [guid]::NewGuid().ToString()
    }

    $payload = @{
        statuses = @(
            @{ id = $StatusIds.backlog; statusReference = $StatusIds.backlog; name = "Backlog"; statusCategory = "TODO"; description = "Item ainda nao iniciado e sem refinamento suficiente para execucao." },
            @{ id = $StatusIds.discovery; statusReference = $refs.discovery; name = "Descoberta"; statusCategory = "TODO"; description = "Item em entendimento, recorte ou validacao de abordagem." },
            @{ id = $StatusIds.ready; statusReference = $refs.ready; name = "Pronto pra dev"; statusCategory = "TODO"; description = "Item refinado e pronto para desenvolvimento." },
            @{ id = $StatusIds.progress; statusReference = $StatusIds.progress; name = "Em andamento"; statusCategory = "IN_PROGRESS"; description = "Item em execucao ativa." },
            @{ id = $StatusIds.review; statusReference = $refs.review; name = "Em revisão"; statusCategory = "IN_PROGRESS"; description = "Item em revisao funcional, tecnica ou validacao final." },
            @{ id = $StatusIds.done; statusReference = $StatusIds.done; name = "Concluído"; statusCategory = "DONE"; description = "Item concluido conforme definicao de pronto." }
        )
        workflows = @(
            @{
                id          = $Workflow.id
                description = $Workflow.description
                statuses    = @(
                    @{ statusReference = $StatusIds.backlog; properties = @{} },
                    @{ statusReference = $refs.discovery; properties = @{} },
                    @{ statusReference = $refs.ready; properties = @{} },
                    @{ statusReference = $StatusIds.progress; properties = @{} },
                    @{ statusReference = $refs.review; properties = @{} },
                    @{ statusReference = $StatusIds.done; properties = @{} }
                )
                transitions = @(
                    @{ id = "11"; type = "GLOBAL"; toStatusReference = $StatusIds.backlog; links = @(); name = "Backlog"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "21"; type = "GLOBAL"; toStatusReference = $refs.discovery; links = @(); name = "Descoberta"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "31"; type = "GLOBAL"; toStatusReference = $refs.ready; links = @(); name = "Pronto pra dev"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "41"; type = "GLOBAL"; toStatusReference = $StatusIds.progress; links = @(); name = "Em andamento"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "51"; type = "GLOBAL"; toStatusReference = $refs.review; links = @(); name = "Em revisão"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "61"; type = "GLOBAL"; toStatusReference = $StatusIds.done; links = @(); name = "Concluído"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{} },
                    @{ id = "1"; type = "INITIAL"; toStatusReference = $StatusIds.backlog; links = @(); name = "Create"; description = ""; actions = @(); validators = @(); triggers = @(); properties = @{ "jira.i18n.title" = "common.forms.create" } }
                )
                version     = @{
                    id            = $Workflow.version.id
                    versionNumber = $Workflow.version.versionNumber
                }
            }
        )
    }

    Invoke-JiraJson -Method "POST" -Uri "$BaseUrl/rest/api/3/workflows/update/validation" -Body @{
        payload = $payload
        validationOptions = @{ levels = @("ERROR", "WARNING") }
    } | Out-Null

    return Invoke-JiraJson -Method "POST" -Uri "$BaseUrl/rest/api/3/workflows/update" -Body $payload
}

$auth = Get-Content -LiteralPath $AuthPath | ConvertFrom-Json
$project = Invoke-JiraJson -Method "GET" -Uri "$($auth.url)/rest/api/3/project/$ProjectKey"
$statusIds = Ensure-ProjectStatuses -ProjectId $project.id -BaseUrl $auth.url
$workflow = Get-ProjectWorkflow -ProjectId $project.id -BaseUrl $auth.url
$result = Publish-StandardWorkflow -BaseUrl $auth.url -Workflow $workflow -StatusIds $statusIds

$result | ConvertTo-Json -Depth 10
