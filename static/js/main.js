(() => {
    "use strict";

    const amountInput = document.getElementById("amount");
    const periodInput = document.getElementById("period-years");
    const periodLabel = document.getElementById("period-label");
    const compareButton = document.getElementById("compare-btn");
    const statusMessage = document.getElementById("status-message");
    const resultsBody = document.querySelector("#results-table tbody");
    const growthCanvas = document.getElementById("growth-chart");
    const resultsCard = document.getElementById("results-card");
    const strategyCards = document.getElementById("strategy-cards");
    const themeToggleButton = document.getElementById("theme-toggle-btn");
    const exportButton = document.getElementById("export-results");
    const exportFormatSelect = document.getElementById("export-format");

    const expectedValueHeader = document.getElementById("expected-value-header");
    const worstHeader = document.getElementById("worst-header");
    const medianHeader = document.getElementById("median-header");
    const bestHeader = document.getElementById("best-header");

    const dateStart = document.getElementById("date-start");
    const dateEnd = document.getElementById("date-end");
    const dateRangeLabel = document.getElementById("date-range-label");
    const minDateLabel = document.getElementById("min-date-label");
    const maxDateLabel = document.getElementById("max-date-label");
    const sliderTrack = document.getElementById("slider-track");

    const multiselect = document.getElementById("strategies-dropdown");
    const multiselectTrigger = multiselect?.querySelector(".multiselect-trigger");
    const multiselectOptions = document.getElementById("strategies-options");
    const selectedCount = multiselect?.querySelector(".selected-count");

    const chartColors = [
        "#2563eb",
        "#10b981",
        "#ef4444",
        "#8b5cf6",
        "#f59e0b",
        "#ec4899",
        "#06b6d4",
        "#84cc16",
        "#6366f1",
        "#d946ef",
    ];

    /** @type {Chart | null} */
    let growthChart = null;
    /** @type {Array<object> | null} */
    let currentResults = null;
    /** @type {Set<number>} */
    const selectedStrategies = new Set();
    /** @type {{labels: string[], datasets: Array<object>} | null} */
    let fullChartData = null;
	/** @type {Array<object>} */
	let allStrategies = []; // Добавить эту строку

    function formatRub(value) {
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue)) {
            return "—";
        }
        return new Intl.NumberFormat("ru-RU", {
            style: "currency",
            currency: "RUB",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        })
            .format(numericValue)
            .replace("RUB", "₽");
    }

    function formatPercent(value, digits = 1) {
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue)) {
            return "—";
        }
        return new Intl.NumberFormat("ru-RU", {
            style: "percent",
            minimumFractionDigits: digits,
            maximumFractionDigits: digits,
        }).format(numericValue);
    }

    function setStatus(text, type = "info") {
        if (!statusMessage) {
            return;
        }

        statusMessage.textContent = text;
        statusMessage.className = "status-message";
        if (type === "error") {
            statusMessage.classList.add("error");
            return;
        }
        if (type === "success") {
            statusMessage.classList.add("success");
        }
    }

    function showLoading() {
        if (!compareButton) {
            return;
        }

        compareButton.disabled = true;
        compareButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Расчет...';
    }

    function hideLoading() {
        if (!compareButton) {
            return;
        }

        compareButton.disabled = false;
        compareButton.innerHTML = '<i class="fas fa-calculator"></i> Рассчитать';
    }

    function fetchCssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    async function fetchJson(url, options = {}) {
        const response = await fetch(url, options);
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || "Request failed.");
        }

        return payload;
    }

    function updateSliderFill() {
        if (!periodInput) {
            return;
        }

        const min = Number(periodInput.min) || 1;
        const max = Number(periodInput.max) || 30;
        const value = Number(periodInput.value) || 10;

        const percentage = ((value - min) / (max - min)) * 100;
        periodInput.style.setProperty("--slider-fill", `${percentage}%`);
    }

    function formatPeriodUnit(periodYears) {
        const safePeriod = Number.isFinite(periodYears) ? periodYears : 1;
        if (safePeriod % 10 === 1 && safePeriod % 100 !== 11) {
            return "год";
        }
        if (
            [2, 3, 4].includes(safePeriod % 10) &&
            ![12, 13, 14].includes(safePeriod % 100)
        ) {
            return "года";
        }
        return "лет";
    }

    function updateResultsTableHeaders(periodYears) {
        if (!expectedValueHeader || !worstHeader || !medianHeader || !bestHeader) {
            return;
        }

        const safePeriod = Number.isFinite(periodYears) && periodYears > 0 ? periodYears : 1;
        const unit = formatPeriodUnit(safePeriod);

        expectedValueHeader.textContent = `Ожидаемая стоимость за ${safePeriod} ${unit}`;
        worstHeader.textContent = `${safePeriod}Y Худший (5%)`;
        medianHeader.textContent = `${safePeriod}Y Медиана (50%)`;
        bestHeader.textContent = `${safePeriod}Y Лучший (95%)`;
    }

    function resolveSelectedPeriodScenarios(result) {
        return result?.selected_period_scenarios || result?.scenarios || null;
    }

    function resolveSelectedPeriodYears(result, fallbackPeriodYears) {
        if (Number.isFinite(result?.selected_period_years) && result.selected_period_years > 0) {
            return Number(result.selected_period_years);
        }
        return fallbackPeriodYears;
    }

    function resolveExpectedValue(result) {
        if (Number.isFinite(result?.expected_selected_period_final_value)) {
            return Number(result.expected_selected_period_final_value);
        }
        if (Number.isFinite(result?.final_value)) {
            return Number(result.final_value);
        }
        return NaN;
    }

    function selectedStrategyIds() {
        return Array.from(selectedStrategies);
    }

    function closeMultiselect() {
        if (!multiselect || !multiselectTrigger) {
            return;
        }

        multiselect.classList.remove("active");
        multiselectTrigger.setAttribute("aria-expanded", "false");
    }

    function positionDropdown() {
        if (!multiselect || !multiselectOptions) {
            return;
        }

        const rect = multiselect.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        const desiredHeight = 300;

        if (spaceBelow < desiredHeight && spaceAbove > spaceBelow) {
            multiselectOptions.classList.add("drop-up");
            multiselectOptions.classList.remove("drop-down");
            return;
        }

        multiselectOptions.classList.add("drop-down");
        multiselectOptions.classList.remove("drop-up");
    }

    function toggleMultiselect() {
        if (!multiselect || !multiselectTrigger) {
            return;
        }

        const willOpen = !multiselect.classList.contains("active");
        multiselect.classList.toggle("active", willOpen);
        multiselectTrigger.setAttribute("aria-expanded", String(willOpen));

        if (willOpen) {
            positionDropdown();
        }
    }

    function updateSelectedCount() {
        if (!selectedCount) {
            return;
        }

        const count = selectedStrategies.size;
        if (count === 0) {
            selectedCount.textContent = "Выберите стратегии";
            selectedCount.classList.remove("has-selections");
            return;
        }

        selectedCount.textContent = `Выбрано: ${count}`;
        selectedCount.classList.add("has-selections");
    }

    function createOption(strategy) {
        const option = document.createElement("div");
        option.className = "multiselect-option";
        option.dataset.id = String(strategy.id);

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = String(strategy.id);

        const content = document.createElement("div");
        content.className = "option-content";

        const name = document.createElement("div");
        name.className = "option-name";
        name.textContent = strategy.name;

        const description = document.createElement("div");
        description.className = "option-desc";
        description.textContent = strategy.description || "";

        content.append(name, description);
        option.append(checkbox, content);

        option.addEventListener("click", (event) => {
            event.stopPropagation();

            checkbox.checked = !checkbox.checked;
            if (checkbox.checked) {
                selectedStrategies.add(Number(strategy.id));
                option.classList.add("selected");
            } else {
                selectedStrategies.delete(Number(strategy.id));
                option.classList.remove("selected");
            }

            updateSelectedCount();
        });

        return option;
    }

    function renderStrategyOptions(strategies) {
		if (!multiselectOptions) {
			return;
		}

		allStrategies = strategies;

		multiselectOptions.innerHTML = "";
		selectedStrategies.clear();

		for (const strategy of strategies) {
			multiselectOptions.appendChild(createOption(strategy));
		}

		updateSelectedCount();
	}

    function createStatBlock(iconClass, labelText, percentText, valueText, percentClass = "") {
        const block = document.createElement("div");
        block.className = "stat-block";

        const header = document.createElement("div");
        header.className = "stat-header";

        const icon = document.createElement("i");
        icon.className = iconClass;

        const label = document.createElement("span");
        label.textContent = labelText;

        header.append(icon, label);

        const percentage = document.createElement("div");
        percentage.className = `percentage ${percentClass}`.trim();
        percentage.textContent = percentText;

        const absoluteValue = document.createElement("div");
        absoluteValue.className = "absolute-value";
        absoluteValue.textContent = valueText;

        block.append(header, percentage, absoluteValue);
        return block;
    }

    function createStrategyMiniCard(result, initialAmount) {
        const card = document.createElement("div");
        card.className = "strategy-mini-card";

        const title = document.createElement("h4");
        title.textContent = result.strategy_name;

        const statsWrapper = document.createElement("div");
        statsWrapper.className = "mini-stats";

        const expectedValue = resolveExpectedValue(result);
        const scenarios = resolveSelectedPeriodScenarios(result);

        const expected = document.createElement("div");
        expected.className = "expected-stat";

        const expectedLabel = document.createElement("span");
        expectedLabel.className = "label";
        expectedLabel.textContent = "Ожидаемая:";

        const expectedValueElement = document.createElement("span");
        expectedValueElement.className = "value";
        expectedValueElement.textContent = formatRub(expectedValue);

        expected.append(expectedLabel, expectedValueElement);
        statsWrapper.appendChild(expected);

        if (scenarios) {
            const worstValue = initialAmount * (1 + Number(scenarios.worst));
            const medianValue = initialAmount * (1 + Number(scenarios.median));
            const bestValue = initialAmount * (1 + Number(scenarios.best));

            statsWrapper.appendChild(
                createStatBlock(
                    "fas fa-arrow-down",
                    "Худший (5%)",
                    formatPercent(scenarios.worst),
                    formatRub(worstValue),
                    Number(scenarios.worst) < 0 ? "negative" : "positive",
                ),
            );

            statsWrapper.appendChild(
                createStatBlock(
                    "fas fa-minus",
                    "Медиана (50%)",
                    formatPercent(scenarios.median),
                    formatRub(medianValue),
                ),
            );

            statsWrapper.appendChild(
                createStatBlock(
                    "fas fa-arrow-up",
                    "Лучший (95%)",
                    formatPercent(scenarios.best),
                    formatRub(bestValue),
                    "positive",
                ),
            );
        }

        card.append(title, statsWrapper);
        return card;
    }

    function renderStrategyCards(results, initialAmount) {
        if (!strategyCards) {
            return;
        }

        strategyCards.innerHTML = "";
        for (const result of results) {
            strategyCards.appendChild(createStrategyMiniCard(result, initialAmount));
        }
    }

    function createScenarioCell(percentValue, rubValue, extraClass = "") {
        const cell = document.createElement("td");
        if (extraClass) {
            cell.classList.add(extraClass);
        }

        const percentElement = document.createElement("div");
        percentElement.textContent = formatPercent(percentValue);

        const valueElement = document.createElement("div");
        valueElement.className = "scenario-value";
        valueElement.textContent = formatRub(rubValue);

        cell.append(percentElement, valueElement);
        return cell;
    }

    // Обновленная функция renderResultsTable с новыми метриками
	function renderResultsTable(results, fallbackPeriodYears, initialAmount) {
		if (!resultsBody) return;

		resultsBody.innerHTML = "";

		const displayedPeriodYears = results.length
			? resolveSelectedPeriodYears(results[0], fallbackPeriodYears)
			: fallbackPeriodYears;
		updateResultsTableHeaders(displayedPeriodYears);

		// Обновляем заголовки таблицы для новых метрик
		updateTableHeadersWithMetrics(displayedPeriodYears);

		for (const result of results) {
			const scenarios = resolveSelectedPeriodScenarios(result);
			const expectedValue = resolveExpectedValue(result);
			
			// Рассчитываем новые метрики
			const metrics = result.detailed_metrics || {};
			
			const row = document.createElement("tr");

			const strategyCell = document.createElement("td");
			strategyCell.className = "strategy-name";
			strategyCell.textContent = result.strategy_name;

			const expectedCell = document.createElement("td");
			expectedCell.className = expectedValue >= initialAmount ? "positive" : "negative";
			expectedCell.textContent = formatRub(expectedValue);

			row.append(strategyCell, expectedCell);

			if (scenarios) {
				const worstValue = initialAmount * (1 + Number(scenarios.worst));
				const medianValue = initialAmount * (1 + Number(scenarios.median));
				const bestValue = initialAmount * (1 + Number(scenarios.best));

				row.appendChild(createScenarioCell(scenarios.worst, worstValue, Number(scenarios.worst) < 0 ? "negative" : "positive"));
				row.appendChild(createScenarioCell(scenarios.median, medianValue));
				row.appendChild(createScenarioCell(scenarios.best, bestValue, "positive"));
			}

			const basicMetrics = result.metrics || {};

			row.appendChild(createMetricsCell(metrics.volatility, "volatility"));
			row.appendChild(createMetricsCell(metrics.max_drawdown, "maxDrawdown", true));
			row.appendChild(createMetricsCell(basicMetrics.sharpe_ratio, "sharpe"));
			row.appendChild(createMetricsCell(metrics.probability_of_profit, "probability"));
			row.appendChild(createMetricsCell(metrics.omega_ratio, "omega"));

			resultsBody.appendChild(row);
		}
	}

	/**
	 * Обновление заголовков таблицы с новыми метриками
	 */
	function updateTableHeadersWithMetrics(periodYears) {
		const headerRow = document.querySelector("#results-table thead tr");
		if (!headerRow) return;

		// Очищаем существующие заголовки после первых 5
		while (headerRow.children.length > 5) {
			headerRow.removeChild(headerRow.lastChild);
		}

		// Добавляем новые заголовки
		const newHeaders = [
			"Волатильность",
			"Max DD",
			"Sharpe Ratio",
			"Win Rate",
			"Omega Ratio"
		];

		newHeaders.forEach(header => {
			const th = document.createElement("th");
			th.textContent = header;
			if (header === "Max DD") th.classList.add("negative");
			if (header === "Sharpe Ratio" || header === "Omega Ratio") th.classList.add("positive");
			headerRow.appendChild(th);
		});
	}

	/**
	 * Создание ячейки для метрики
	 */
	function createMetricsCell(value, metricType, isNegative = false) {
		const cell = document.createElement("td");
		
		if (value === null || value === undefined || !Number.isFinite(value)) {
			cell.textContent = "—";
			return cell;
		}
		
		let formattedValue = "";
		let extraClass = "";
		
		switch (metricType) {
			case "volatility":
				formattedValue = formatPercent(value);
				extraClass = value > 0.2 ? "warning" : "";
				break;
			case "maxDrawdown":
				formattedValue = formatPercent(Math.abs(value));
				extraClass = "negative";
				break;
			case "sharpe":
				formattedValue = value.toFixed(2);
				extraClass = value > 1 ? "positive" : value < 0 ? "negative" : "";
				break;
			case "probability":
				formattedValue = formatPercent(value);
				extraClass = value > 0.5 ? "positive" : "";
				break;
			case "omega":
				formattedValue = value.toFixed(2);
				extraClass = value > 1.5 ? "positive" : value < 1 ? "negative" : "";
				break;
			default:
				formattedValue = String(value);
		}
		
		if (extraClass) cell.classList.add(extraClass);
		cell.textContent = formattedValue;
		
		return cell;
	}

    function filterLabelsByYear(labels, startYear, endYear) {
        return labels.filter((dateString) => {
            const year = new Date(dateString).getFullYear();
            return year >= startYear && year <= endYear;
        });
    }

    function filterChartByDate(startYear, endYear) {
        if (!fullChartData || !growthChart) {
            return;
        }

        const filteredLabels = filterLabelsByYear(fullChartData.labels, startYear, endYear);
        const filteredDatasets = fullChartData.datasets.map((dataset) => ({
            ...dataset,
            data: dataset.data.filter((_, index) => {
                const year = new Date(fullChartData.labels[index]).getFullYear();
                return year >= startYear && year <= endYear;
            }),
        }));

        growthChart.data.labels = filteredLabels;
        growthChart.data.datasets = filteredDatasets;
        growthChart.update();
    }

    function updateDateRange() {
        if (!dateStart || !dateEnd || !dateRangeLabel || !sliderTrack) {
            return;
        }

        let startYear = Number(dateStart.value);
        let endYear = Number(dateEnd.value);

        if (startYear > endYear) {
            if (document.activeElement === dateStart) {
                startYear = endYear;
                dateStart.value = String(startYear);
            } else {
                endYear = startYear;
                dateEnd.value = String(endYear);
            }
        }

        dateRangeLabel.textContent = `${startYear}-${endYear}`;
        if (minDateLabel) {
            minDateLabel.textContent = String(startYear);
        }
        if (maxDateLabel) {
            maxDateLabel.textContent = String(endYear);
        }

        const min = Number(dateStart.min);
        const max = Number(dateStart.max);
        const totalRange = max - min || 1;
        const startPosition = ((startYear - min) / totalRange) * 100;
        const endPosition = ((endYear - min) / totalRange) * 100;

        sliderTrack.style.setProperty("--start-pos", `${startPosition}%`);
        sliderTrack.style.setProperty("--end-pos", `${endPosition}%`);

        if (fullChartData) {
            filterChartByDate(startYear, endYear);
        }
    }

    function applyDateBoundsFromGrowthData(growthData) {
        if (!Array.isArray(growthData) || growthData.length === 0 || !dateStart || !dateEnd) {
            return;
        }

        const years = growthData
            .map((point) => new Date(point.date).getFullYear())
            .filter((year) => Number.isFinite(year));

        if (!years.length) {
            return;
        }

        const minYear = Math.min(...years);
        const maxYear = Math.max(...years);

        dateStart.min = String(minYear);
        dateStart.max = String(maxYear);
        dateEnd.min = String(minYear);
        dateEnd.max = String(maxYear);

        dateStart.value = String(minYear);
        dateEnd.value = String(maxYear);

        if (minDateLabel) {
            minDateLabel.textContent = String(minYear);
        }
        if (maxDateLabel) {
            maxDateLabel.textContent = String(maxYear);
        }
        if (dateRangeLabel) {
            dateRangeLabel.textContent = `${minYear}-${maxYear}`;
        }

        sliderTrack?.style.setProperty("--start-pos", "0%");
        sliderTrack?.style.setProperty("--end-pos", "100%");
    }

    function renderGrowthChart(results) {
        if (!growthCanvas) {
            return;
        }

        if (growthChart) {
            growthChart.destroy();
        }

        const labels = results.length
            ? (results[0].growth_chart_data || []).map((point) => point.date)
            : [];

        const datasets = results.map((result, index) => ({
            label: result.strategy_name,
            data: (result.growth_chart_data || []).map((point) => point.value),
            borderColor: chartColors[index % chartColors.length],
            backgroundColor: `${chartColors[index % chartColors.length]}20`,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: chartColors[index % chartColors.length],
            pointHoverBorderColor: "white",
            pointHoverBorderWidth: 2,
            tension: 0.1,
            fill: false,
        }));

        fullChartData = {
            labels,
            datasets: JSON.parse(JSON.stringify(datasets)),
        };

        const startYear = Number(dateStart?.value || 0);
        const endYear = Number(dateEnd?.value || 9999);

        const filteredLabels = filterLabelsByYear(labels, startYear, endYear);
        const filteredDatasets = datasets.map((dataset) => ({
            ...dataset,
            data: dataset.data.filter((_, index) => {
                const year = new Date(labels[index]).getFullYear();
                return year >= startYear && year <= endYear;
            }),
        }));

        growthChart = new Chart(growthCanvas, {
            type: "line",
            data: {
                labels: filteredLabels,
                datasets: filteredDatasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: "top",
                        labels: {
                            color: fetchCssVar("--text") || "#0f172a",
                            usePointStyle: true,
                            pointStyle: "circle",
                        },
                    },
                    tooltip: {
                        backgroundColor: fetchCssVar("--card") || "#ffffff",
                        titleColor: fetchCssVar("--text") || "#0f172a",
                        bodyColor: fetchCssVar("--text-secondary") || "#475569",
                        borderColor: fetchCssVar("--border") || "#e2e8f0",
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label(context) {
                                const strategyLabel = context.dataset.label || "";
                                const value = context.parsed?.y;
                                return `${strategyLabel}: ${formatRub(value)}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: {
                            color: fetchCssVar("--border") || "#e2e8f0",
                        },
                        ticks: {
                            color: fetchCssVar("--text-muted") || "#64748b",
                            maxTicksLimit: 8,
                            maxRotation: 45,
                            minRotation: 45,
                        },
                    },
                    y: {
                        grid: {
                            color: fetchCssVar("--border") || "#e2e8f0",
                        },
                        ticks: {
                            color: fetchCssVar("--text-muted") || "#64748b",
                            callback(value) {
                                return formatRub(value);
                            },
                        },
                    },
                },
            },
        });
    }

    function csvEscape(value) {
        return `"${String(value).replaceAll('"', '""')}"`;
    }

    function getChartExportRows() {
        if (!fullChartData || !Array.isArray(fullChartData.labels) || !Array.isArray(fullChartData.datasets)) {
            return { headers: [], rows: [] };
        }

        const headers = ["Дата", ...fullChartData.datasets.map((dataset) => dataset.label || "Стратегия")];
        const rows = fullChartData.labels.map((label, index) => {
            const values = fullChartData.datasets.map((dataset) => {
                const value = Number(dataset?.data?.[index]);
                return Number.isFinite(value) ? value.toFixed(2) : "";
            });
            return [label, ...values];
        });

        return { headers, rows };
    }

    function buildExportData(initialAmount) {
        const summaryHeaders = [
            "Стратегия",
            "Ожидаемая стоимость (₽)",
            "Худший случай (%)",
            "Худший случай (₽)",
            "Медиана (%)",
            "Медиана (₽)",
            "Лучший случай (%)",
            "Лучший случай (₽)",
        ];

        const summaryRows = [];

        for (const result of currentResults || []) {
            const scenarios = resolveSelectedPeriodScenarios(result);
            const expectedValue = resolveExpectedValue(result);

            const worst = Number(scenarios?.worst ?? NaN);
            const median = Number(scenarios?.median ?? NaN);
            const best = Number(scenarios?.best ?? NaN);

            const worstValue = initialAmount * (1 + worst);
            const medianValue = initialAmount * (1 + median);
            const bestValue = initialAmount * (1 + best);

            summaryRows.push([
                result.strategy_name,
                Number.isFinite(expectedValue) ? expectedValue.toFixed(2) : "",
                Number.isFinite(worst) ? (worst * 100).toFixed(4) : "",
                Number.isFinite(worstValue) ? worstValue.toFixed(2) : "",
                Number.isFinite(median) ? (median * 100).toFixed(4) : "",
                Number.isFinite(medianValue) ? medianValue.toFixed(2) : "",
                Number.isFinite(best) ? (best * 100).toFixed(4) : "",
                Number.isFinite(bestValue) ? bestValue.toFixed(2) : "",
            ]);
        }

        return {
            summary: { headers: summaryHeaders, rows: summaryRows },
            chart: getChartExportRows(),
        };
    }

    function exportToCSV() {
        if (!currentResults || !currentResults.length) {
            setStatus("Нет данных для экспорта.", "error");
            return;
        }

        const initialAmount = Number(amountInput?.value || 0);
        const data = buildExportData(initialAmount);

        const sections = [
            ["Ключевые результаты"],
            data.summary.headers,
            ...data.summary.rows,
            [],
            ["Данные графика роста инвестиций"],
            data.chart.headers,
            ...data.chart.rows,
        ];

        const csv = sections
            .map((row) => (row.length ? row.map((value) => csvEscape(value)).join(",") : ""))
            .join("\n");

        // BOM improves Cyrillic compatibility in Excel and other spreadsheet software.
        const csvWithBom = `\uFEFF${csv}`;
        const blob = new Blob([csvWithBom], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `investment_results_${new Date().toISOString().split("T")[0]}.csv`;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
        setStatus("CSV экспорт завершен успешно.", "success");
    }

    function applyWorksheetHeaderStyle(worksheet, columnCount) {
        const headerRow = worksheet.getRow(1);
        headerRow.font = { bold: true };
        headerRow.fill = {
            type: "pattern",
            pattern: "solid",
            fgColor: { argb: "FFE5E7EB" },
        };
        for (let index = 1; index <= columnCount; index += 1) {
            const cell = headerRow.getCell(index);
            cell.border = {
                top: { style: "thin", color: { argb: "FFCBD5E1" } },
                left: { style: "thin", color: { argb: "FFCBD5E1" } },
                bottom: { style: "thin", color: { argb: "FFCBD5E1" } },
                right: { style: "thin", color: { argb: "FFCBD5E1" } },
            };
            cell.alignment = { vertical: "middle", horizontal: "center" };
        }
    }

    function appendDataToWorksheet(workbook, title, headers, rows) {
        const worksheet = workbook.addWorksheet(title);
        worksheet.addRow(headers);
        for (const row of rows) {
            worksheet.addRow(row);
        }

        applyWorksheetHeaderStyle(worksheet, headers.length);
        worksheet.columns.forEach((column) => {
            column.width = 24;
        });

        return worksheet;
    }

    async function exportToExcel() {
        if (!currentResults || !currentResults.length) {
            setStatus("Нет данных для экспорта.", "error");
            return;
        }

        if (!window.ExcelJS) {
            setStatus("Библиотека ExcelJS не загружена. Повторите попытку позже.", "error");
            return;
        }

        try {
            const initialAmount = Number(amountInput?.value || 0);
            const data = buildExportData(initialAmount);

            const workbook = new window.ExcelJS.Workbook();
            workbook.creator = "Investment Strategist";
            workbook.created = new Date();

            appendDataToWorksheet(
                workbook,
                "Ключевые результаты",
                data.summary.headers,
                data.summary.rows,
            );
            appendDataToWorksheet(
                workbook,
                "Данные графика",
                data.chart.headers,
                data.chart.rows,
            );

            const chartSheet = workbook.addWorksheet("График");
            chartSheet.getCell("A1").value = "Диаграмма роста инвестиций";
            chartSheet.getCell("A1").font = { bold: true, size: 14 };

            if (growthCanvas instanceof HTMLCanvasElement) {
                const chartImage = growthCanvas.toDataURL("image/png", 1.0);
                const imageId = workbook.addImage({
                    base64: chartImage,
                    extension: "png",
                });
                chartSheet.addImage(imageId, "A3:L28");
            }

            const buffer = await workbook.xlsx.writeBuffer();
            const blob = new Blob([buffer], {
                type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            });

            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `investment_results_${new Date().toISOString().split("T")[0]}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            setStatus("Excel экспорт завершен успешно.", "success");
        } catch (error) {
            setStatus(error.message || "Ошибка экспорта Excel.", "error");
        }
    }

    async function exportResults() {
        const selectedFormat = exportFormatSelect?.value || "csv";
        if (selectedFormat === "xlsx") {
            await exportToExcel();
            return;
        }
        exportToCSV();
    }

    function initTheme() {
        const savedTheme = localStorage.getItem("theme");
        if (savedTheme === "dark") {
            document.documentElement.setAttribute("data-theme", "dark");
            if (themeToggleButton) {
                themeToggleButton.innerHTML = '<i class="fas fa-sun"></i>';
            }
        }
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        if (currentTheme === "dark") {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("theme", "light");
            if (themeToggleButton) {
                themeToggleButton.innerHTML = '<i class="fas fa-moon"></i>';
            }
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
            if (themeToggleButton) {
                themeToggleButton.innerHTML = '<i class="fas fa-sun"></i>';
            }
        }

        if (currentResults) {
            renderGrowthChart(currentResults);
        }
    }

    async function loadStrategies() {
        setStatus("Загрузка стратегий...");

        try {
            const payload = await fetchJson("/api/strategies");
            const strategies = payload.strategies || [];

            renderStrategyOptions(strategies);

            const sampleGrowthData = strategies.find((strategy) =>
                Array.isArray(strategy.growth_chart_data) && strategy.growth_chart_data.length > 0,
            )?.growth_chart_data;

            if (sampleGrowthData) {
                applyDateBoundsFromGrowthData(sampleGrowthData);
            }

            setStatus("Выберите стратегии и нажмите Рассчитать", "success");
        } catch (error) {
            setStatus(error.message || "Не удалось загрузить стратегии.", "error");
        }
    }

    async function runSimulation() {
		const amount = Number(amountInput?.value);
		const periodYears = Number(periodInput?.value);
		const strategyIds = selectedStrategyIds();

		if (!Number.isFinite(amount) || amount <= 0) {
			setStatus("Пожалуйста, введите корректную сумму.", "error");
			return;
		}

		if (!Number.isFinite(periodYears) || periodYears <= 0) {
			setStatus("Пожалуйста, выберите корректный срок инвестирования.", "error");
			return;
		}

		if (!strategyIds.length) {
			setStatus("Пожалуйста, выберите хотя бы одну стратегию.", "error");
			return;
		}

		// Очищаем секцию рейтинга при новом расчете
		clearRankingSection();

		showLoading();

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

			const results = payload.results || [];
			currentResults = results;

			if (results.length && Array.isArray(results[0].growth_chart_data)) {
				applyDateBoundsFromGrowthData(results[0].growth_chart_data);
			}

			renderStrategyCards(results, amount);
			renderResultsTable(results, periodYears, amount);
			renderGrowthChart(results);

			if (resultsCard) {
				resultsCard.style.display = "block";
				resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
			}

			setStatus("Симуляция успешно завершена.", "success");
		} catch (error) {
			setStatus(error.message || "Симуляция не удалась.", "error");
		} finally {
			hideLoading();
		}
	}

    function onPeriodChange() {
        const periodYears = Number(periodInput?.value);

        if (periodLabel) {
            periodLabel.textContent = String(periodYears);
        }

        updateSliderFill();
        updateResultsTableHeaders(periodYears);
    }

    amountInput?.addEventListener("blur", () => {
        const value = Number(amountInput.value);
        if (value < 1) {
            amountInput.value = "1";
            return;
        }
        if (value > 1000000000) {
            amountInput.value = "1000000000";
        }
    });

    periodInput?.addEventListener("input", onPeriodChange);
    compareButton?.addEventListener("click", runSimulation);
    exportButton?.addEventListener("click", exportResults);
    dateStart?.addEventListener("input", updateDateRange);
    dateEnd?.addEventListener("input", updateDateRange);

    multiselectTrigger?.addEventListener("click", toggleMultiselect);

    document.addEventListener("click", (event) => {
        if (multiselect && event.target instanceof Node && !multiselect.contains(event.target)) {
            closeMultiselect();
        }
    });

    window.addEventListener("resize", () => {
        if (multiselect?.classList.contains("active")) {
            positionDropdown();
        }
    });

    window.addEventListener(
        "scroll",
        () => {
            if (multiselect?.classList.contains("active")) {
                positionDropdown();
            }
        },
        { passive: true },
    );

    themeToggleButton?.addEventListener("click", toggleTheme);

    initTheme();
    onPeriodChange();
    updateDateRange();

    if (resultsCard) {
        resultsCard.style.display = "none";
    }
	
	/**
	 * Очищает секцию с рейтингом стратегий
	 */
	function clearRankingSection() {
		const existingSection = document.querySelector('.ranking-section');
		if (existingSection) {
			existingSection.remove();
		}
	}

    loadStrategies();
	
	// ==================== Ranking Functions ====================

	/**
	 * Ранжирует стратегии по ожидаемой доходности
	 * @param {Array} results - массив результатов симуляции
	 * @param {number} initialAmount - начальная сумма
	 * @returns {Array} - отсортированный массив стратегий
	 */
	function rankStrategiesByProfitability(results, initialAmount) {
		if (!results || !results.length) return [];

		return results
			.map((result) => ({
				strategyId: result.strategy_id,
				strategyName: result.strategy_name,
				expectedValue: resolveExpectedValue(result),
				scenarios: resolveSelectedPeriodScenarios(result),
				totalReturn: (resolveExpectedValue(result) / initialAmount) - 1,
				cagr: Math.pow(resolveExpectedValue(result) / initialAmount, 1 / (Number(periodInput?.value) || 1)) - 1,
				sharpeRatio: calculateSharpeRatioFromResult(result),
				volatility: result.detailed_metrics?.volatility ?? null
			}))
			.sort((a, b) => b.expectedValue - a.expectedValue);
	}
	
	/**
	 * Расчет коэффициента Шарпа из результатов
	 */
	function calculateSharpeRatioFromResult(result) {
		const sharpeRatio = Number(result?.metrics?.sharpe_ratio);
		return Number.isFinite(sharpeRatio) ? sharpeRatio : null;
	}


	/**
	 * Создает HTML для отображения ранжированных стратегий
	 */
	function renderRankingSection(rankedStrategies) {
		// Удаляем существующую секцию если есть
		const existingSection = document.querySelector('.ranking-section');
		if (existingSection) {
			existingSection.remove();
		}

		if (!rankedStrategies.length) return;

		const paramsCard = document.querySelector('.params-card');
		if (!paramsCard) return;

		const rankingSection = document.createElement('div');
		rankingSection.className = 'ranking-section';
		rankingSection.innerHTML = `
			<h4>
				<i class="fas fa-trophy"></i>
				Рейтинг стратегий по ожидаемой доходности
			</h4>
			<div class="ranking-list">
				${rankedStrategies.map((strategy, index) => `
					<div class="ranking-item">
						<span class="rank">#${index + 1}</span>
						<span class="name">${escapeHtml(strategy.strategyName)}</span>
						<span class="value">${formatRub(strategy.expectedValue)}</span>
						<span class="badge">+${formatPercent(strategy.totalReturn)}</span>
					</div>
				`).join('')}
			</div>
			<div class="ranking-footer" style="margin-top: 0.5rem; font-size: 0.65rem; color: var(--text-muted); text-align: center;">
				<i class="fas fa-chart-line"></i> Ранжирование по ожидаемой финальной стоимости
			</div>
		`;

		// Вставляем после кнопок
		const rankingButtons = document.querySelector('.ranking-buttons');
		if (rankingButtons) {
			rankingButtons.parentNode.insertBefore(rankingSection, rankingButtons.nextSibling);
		} else {
			paramsCard.appendChild(rankingSection);
		}
	}

	/**
	 * Экранирование HTML специальных символов
	 */
	function escapeHtml(str) {
		if (!str) return '';
		return str
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#39;');
	}

	/**
	 * Запускает симуляцию для всех стратегий и ранжирует их
	 */
	async function runRanking() {
		const amount = Number(amountInput?.value);
		const periodYears = Number(periodInput?.value);

		if (!Number.isFinite(amount) || amount <= 0) {
			setStatus("Пожалуйста, введите корректную сумму для ранжирования.", "error");
			return;
		}

		if (!Number.isFinite(periodYears) || periodYears <= 0) {
			setStatus("Пожалуйста, выберите корректный срок инвестирования.", "error");
			return;
		}

		// Получаем ID всех доступных стратегий
		const allStrategyIds = allStrategies.map(s => s.id);
		if (!allStrategyIds.length) {
			setStatus("Нет доступных стратегий для ранжирования.", "error");
			return;
		}

		setStatus("Анализ всех стратегий...", "info");
		showLoading();

		try {
			const payload = await fetchJson("/api/simulate", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					amount,
					period_years: periodYears,
					strategy_ids: allStrategyIds,
				}),
			});

			const results = payload.results || [];
			if (!results.length) {
				setStatus("Не удалось получить результаты симуляции.", "error");
				return;
			}

			// Ранжируем стратегии
			const ranked = rankStrategiesByProfitability(results, amount);
			
			// Показываем секцию с ранжированием
			renderRankingSection(ranked);
			
			// Обновляем основной интерфейс
			currentResults = results;
			renderStrategyCards(results, amount);
			renderResultsTable(results, periodYears, amount);
			renderGrowthChart(results);
			
			if (resultsCard) {
				resultsCard.style.display = "block";
			}
			
			setStatus(`Проанализировано ${ranked.length} стратегий. Лучшая: ${ranked[0]?.strategyName || '—'}`, "success");
		} catch (error) {
			setStatus(error.message || "Ошибка при анализе стратегий.", "error");
		} finally {
			hideLoading();
		}
	}

	// Добавить обработчик кнопки в Event Listeners
	const rankStrategiesBtn = document.getElementById("rank-strategies-btn");
	rankStrategiesBtn?.addEventListener("click", runRanking);
	
})();
