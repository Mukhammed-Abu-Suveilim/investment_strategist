(() => {
    "use strict";

    const amountInput = document.getElementById("amount");
    const periodInput = document.getElementById("period-years");
    const periodLabel = document.getElementById("period-label");
    const strategiesSelect = document.getElementById("strategies");
    const compareButton = document.getElementById("compare-btn");
    const statusMessage = document.getElementById("status-message");
    const resultsBody = document.querySelector("#results-table tbody");
    const expectedValueHeader = document.getElementById("expected-value-header");
    const worstHeader = document.getElementById("worst-header");
    const medianHeader = document.getElementById("median-header");
    const bestHeader = document.getElementById("best-header");
    const growthCanvas = document.getElementById("growth-chart");

    let growthChart = null;

    function formatRub(value) {
        return new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
            maximumFractionDigits: 2,
        }).format(value);
    }

    function formatPercent(value) {
        return `${(value * 100).toFixed(2)}%`;
    }

    function setStatus(text, isError = false) {
        statusMessage.textContent = text;
        statusMessage.style.color = isError ? "#b91c1c" : "#6b7280";
    }

    function selectedStrategyIds() {
        return Array.from(strategiesSelect.selectedOptions).map((option) => Number(option.value));
    }

    async function fetchJson(url, options = {}) {
        const response = await fetch(url, options);
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Request failed.");
        }
        return payload;
    }

    function renderStrategyOptions(strategies) {
        strategiesSelect.innerHTML = "";
        for (const strategy of strategies) {
            const option = document.createElement("option");
            option.value = String(strategy.id);
            option.textContent = strategy.name;
            strategiesSelect.appendChild(option);
        }
    }

    function formatPeriodUnit(periodYears) {
        return periodYears === 1 ? "Year" : "Years";
    }

    function updateResultsTableHeaders(periodYears) {
        const safePeriod = Number.isFinite(periodYears) && periodYears > 0 ? periodYears : 1;
        const periodUnit = formatPeriodUnit(safePeriod);
        const periodShortLabel = `${safePeriod}Y`;

        expectedValueHeader.textContent = `Expected Value in ${safePeriod} ${periodUnit} (RUB)`;
        worstHeader.textContent = `${periodShortLabel} Worst (5%)`;
        medianHeader.textContent = `${periodShortLabel} Median (50%)`;
        bestHeader.textContent = `${periodShortLabel} Best (95%)`;
    }

    function resolveSelectedPeriodScenarios(result) {
        if (result.selected_period_scenarios) {
            return result.selected_period_scenarios;
        }
        return result.scenarios;
    }

    function resolveSelectedPeriodYears(result, fallbackPeriodYears) {
        if (Number.isFinite(result.selected_period_years) && result.selected_period_years > 0) {
            return Number(result.selected_period_years);
        }
        return fallbackPeriodYears;
    }

    function renderResultsTable(results, fallbackPeriodYears) {
        resultsBody.innerHTML = "";

        const displayedPeriodYears = results.length > 0
            ? resolveSelectedPeriodYears(results[0], fallbackPeriodYears)
            : fallbackPeriodYears;
        updateResultsTableHeaders(displayedPeriodYears);

        for (const result of results) {
            const selectedPeriodScenarios = resolveSelectedPeriodScenarios(result);
            const expectedSelectedPeriodFinalValue =
                result.expected_selected_period_final_value ?? result.final_value;

            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${result.strategy_name}</td>
                <td>${formatRub(expectedSelectedPeriodFinalValue)}</td>
                <td>${formatPercent(selectedPeriodScenarios.worst)}</td>
                <td>${formatPercent(selectedPeriodScenarios.median)}</td>
                <td>${formatPercent(selectedPeriodScenarios.best)}</td>
            `;
            resultsBody.appendChild(row);
        }
    }

    function renderGrowthChart(results) {
        if (growthChart) {
            growthChart.destroy();
        }

        const labels = results.length > 0
            ? results[0].growth_chart_data.map((point) => point.date)
            : [];

        const datasets = results.map((result, index) => ({
            label: result.strategy_name,
            data: result.growth_chart_data.map((point) => point.value),
            borderColor: ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#d97706"][index % 5],
            borderWidth: 2,
            fill: false,
            pointRadius: 0,
            tension: 0.1,
        }));

        growthChart = new Chart(growthCanvas, {
            type: "line",
            data: {
                labels,
                datasets,
            },
            options: {
                responsive: true,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                scales: {
                    x: {
                        ticks: {
                            maxTicksLimit: 10,
                        },
                    },
                    y: {
                        ticks: {
                            callback(value) {
                                return formatRub(value);
                            },
                        },
                    },
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label(context) {
                                return `${context.dataset.label}: ${formatRub(context.parsed.y)}`;
                            },
                        },
                    },
                },
            },
        });
    }

    async function loadStrategies() {
        setStatus("Loading strategies...");
        const payload = await fetchJson("/api/strategies");
        renderStrategyOptions(payload.strategies);
        setStatus("Select one or more strategies and click Compare.");
    }

    async function runSimulation() {
        const amount = Number(amountInput.value);
        const periodYears = Number(periodInput.value);
        const strategyIds = selectedStrategyIds();

        if (!amount || amount <= 0) {
            setStatus("Please enter a valid amount.", true);
            return;
        }

        if (strategyIds.length === 0) {
            setStatus("Please select at least one strategy.", true);
            return;
        }

        setStatus("Running simulation...");
        compareButton.disabled = true;

        try {
            const payload = await fetchJson("/api/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    amount,
                    period_years: periodYears,
                    strategy_ids: strategyIds,
                }),
            });

            renderResultsTable(payload.results, periodYears);
            renderGrowthChart(payload.results);
            setStatus("Simulation completed successfully.");
        } catch (error) {
            setStatus(error.message || "Simulation failed.", true);
        } finally {
            compareButton.disabled = false;
        }
    }

    periodInput.addEventListener("input", () => {
        const periodYears = Number(periodInput.value);
        periodLabel.textContent = periodInput.value;
        updateResultsTableHeaders(periodYears);
    });

    compareButton.addEventListener("click", runSimulation);

    updateResultsTableHeaders(Number(periodInput.value));

    loadStrategies().catch((error) => {
        setStatus(error.message || "Failed to load strategies.", true);
    });
})();
