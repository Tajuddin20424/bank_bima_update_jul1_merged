$(document).ready(function () {

    const CONFIG = window.PATIENT_REPORT_CONFIG || {};

    const PATIENT_DATA_URL = CONFIG.patientDataUrl || "/dcc/patients/__PATIENT_ID__/data/";
    const LOAD_TEMPLATE_URL = CONFIG.loadTemplateUrl || "/dcc/load-report-template/";
    const SAVE_URL = CONFIG.saveUrl || "/dcc/patients/prescriptions/save/";
    const OLD_PRESCRIPTION_URL = CONFIG.oldPrescriptionUrl || "/dcc/patients/prescriptions/__PATIENT_ID__/";

    let currentWritingMode = "english";
    let extraFieldCounter = 0;

    /* =====================================================
       BASIC HELPERS
    ===================================================== */
    function getQueryParam(param) {
        let params = new URLSearchParams(window.location.search);
        return params.get(param);
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return "";

        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getFirstAvailable(data, keys, fallback = "") {
        if (!data) return fallback;

        for (let i = 0; i < keys.length; i++) {
            let key = keys[i];

            if (data[key] !== undefined && data[key] !== null && data[key] !== "") {
                return data[key];
            }
        }

        if (data.patient) {
            for (let i = 0; i < keys.length; i++) {
                let key = keys[i];

                if (data.patient[key] !== undefined && data.patient[key] !== null && data.patient[key] !== "") {
                    return data.patient[key];
                }
            }
        }

        if (data.data) {
            for (let i = 0; i < keys.length; i++) {
                let key = keys[i];

                if (data.data[key] !== undefined && data.data[key] !== null && data.data[key] !== "") {
                    return data.data[key];
                }
            }
        }

        return fallback;
    }

    function setHeaderField(fieldName, value) {
        let input = $(`#headerFields .header-input[data-field='${fieldName}']`);

        if (input.length) {
            input.val(value || "").trigger("input");
        }
    }

    function updateModalScale() {
        const modalBody = $(".preview-modal-body");

        if (!modalBody.length) return;

        const availableWidth = modalBody.width() - 36;
        const availableHeight = Math.min(window.innerHeight - 170, 780);

        let scaleByWidth = availableWidth / 794;
        let scaleByHeight = availableHeight / 1123;

        let scale = Math.min(scaleByWidth, scaleByHeight, 0.78);
        scale = Math.max(scale, 0.45);

        document.documentElement.style.setProperty("--modal-scale", scale);
    }

    function updateEditorEmptyState(editor) {
        if ($(editor).text().trim() === "") {
            $(editor).addClass("empty");
        } else {
            $(editor).removeClass("empty");
        }
    }

    function placeCursorAtEnd(element) {
        element.focus();

        let range = document.createRange();
        let selection = window.getSelection();

        range.selectNodeContents(element);
        range.collapse(false);

        selection.removeAllRanges();
        selection.addRange(range);
    }

    function setDefaultDate() {
        let today = new Date().toISOString().substr(0, 10);
        let dateInput = $("#headerFields input[data-field='Date']");

        if (!dateInput.val()) {
            dateInput.val(today);
        }

        refreshReportPreview();
    }

    /* =====================================================
       CUSTOM UNDO / REDO
    ===================================================== */
    function initEditorHistory(editor) {
        editor.data("undo-stack", []);
        editor.data("redo-stack", []);
        editor.data("last-html", editor.html());
    }

    function saveEditorHistory(editor) {
        let undoStack = editor.data("undo-stack") || [];
        let currentHtml = editor.html();
        let lastHtml = editor.data("last-html");

        if (currentHtml === lastHtml) return;

        undoStack.push(lastHtml);

        if (undoStack.length > 100) {
            undoStack.shift();
        }

        editor.data("undo-stack", undoStack);
        editor.data("redo-stack", []);
        editor.data("last-html", currentHtml);
    }

    function undoEditor(editor, field) {
        let undoStack = editor.data("undo-stack") || [];
        let redoStack = editor.data("redo-stack") || [];

        if (undoStack.length === 0) return;

        let currentHtml = editor.html();
        let previousHtml = undoStack.pop();

        redoStack.push(currentHtml);
        editor.html(previousHtml);

        editor.data("undo-stack", undoStack);
        editor.data("redo-stack", redoStack);
        editor.data("last-html", previousHtml);

        placeCursorAtEnd(editor[0]);
        syncEditorToOriginal(editor, field);
        updateEditorEmptyState(editor);
        refreshReportPreview();
    }

    function redoEditor(editor, field) {
        let undoStack = editor.data("undo-stack") || [];
        let redoStack = editor.data("redo-stack") || [];

        if (redoStack.length === 0) return;

        let currentHtml = editor.html();
        let nextHtml = redoStack.pop();

        undoStack.push(currentHtml);
        editor.html(nextHtml);

        editor.data("undo-stack", undoStack);
        editor.data("redo-stack", redoStack);
        editor.data("last-html", nextHtml);

        placeCursorAtEnd(editor[0]);
        syncEditorToOriginal(editor, field);
        updateEditorEmptyState(editor);
        refreshReportPreview();
    }

    /* =====================================================
       RICH EDITOR
    ===================================================== */
    function wrapTypedText(text) {
        let span = document.createElement("span");
        span.className = currentWritingMode === "bijoy" ? "typed-bijoy" : "typed-english";
        span.textContent = text;
        return span;
    }

    function insertStyledText(text) {
        const selection = window.getSelection();

        if (!selection || !selection.rangeCount) return;

        let range = selection.getRangeAt(0);
        range.deleteContents();

        let node = wrapTypedText(text);
        range.insertNode(node);

        range.setStartAfter(node);
        range.setEndAfter(node);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    function insertLineBreak() {
        const selection = window.getSelection();

        if (!selection || !selection.rangeCount) return;

        let range = selection.getRangeAt(0);
        range.deleteContents();

        let br = document.createElement("br");
        range.insertNode(br);

        range.setStartAfter(br);
        range.setEndAfter(br);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    function syncEditorToOriginal(editor, field) {
        let html = $(editor).html();
        let plain = $(editor).text();

        $(field).val(plain);
        $(field).attr("data-mixed-html", html);
    }

    function makeRichEditor(originalField, labelName) {
        let field = $(originalField);

        if (field.data("rich-ready") === true) {
            return field.next(".rich-editor");
        }

        let currentValue = field.val() || "";
        let placeholder = field.attr("placeholder") || "Write details";

        field
            .data("rich-ready", true)
            .addClass("original-writing-field")
            .attr("data-report-label", labelName);

        let editor = $("<div></div>")
            .addClass("rich-editor empty")
            .attr("contenteditable", "true")
            .attr("spellcheck", "false")
            .attr("data-placeholder", placeholder)
            .attr("data-report-label", labelName);

        if (currentValue.trim()) {
            editor.html(`<span class="typed-english">${escapeHtml(currentValue)}</span>`);
            editor.removeClass("empty");
        }

        field.after(editor);
        initEditorHistory(editor);

        editor.on("keydown", function (event) {
            const isShortcut = event.ctrlKey || event.metaKey;
            const key = event.key.toLowerCase();

            if (isShortcut && key === "z" && !event.shiftKey) {
                event.preventDefault();
                undoEditor(editor, field);
                return;
            }

            if (
                (isShortcut && key === "y") ||
                (isShortcut && event.shiftKey && key === "z")
            ) {
                event.preventDefault();
                redoEditor(editor, field);
                return;
            }

            if (isShortcut && key === "b") {
                event.preventDefault();

                saveEditorHistory(editor);
                document.execCommand("bold", false, null);

                editor.data("last-html", editor.html());
                syncEditorToOriginal(editor, field);
                refreshReportPreview();
                return;
            }

            if (isShortcut && key === "i") {
                event.preventDefault();

                saveEditorHistory(editor);
                document.execCommand("italic", false, null);

                editor.data("last-html", editor.html());
                syncEditorToOriginal(editor, field);
                refreshReportPreview();
                return;
            }

            if (isShortcut && key === "u") {
                event.preventDefault();

                saveEditorHistory(editor);
                document.execCommand("underline", false, null);

                editor.data("last-html", editor.html());
                syncEditorToOriginal(editor, field);
                refreshReportPreview();
                return;
            }
        });

        editor.on("beforeinput", function (event) {
            let e = event.originalEvent;
            if (!e) return;

            if (e.inputType === "insertText") {
                e.preventDefault();

                saveEditorHistory(editor);
                insertStyledText(e.data || "");

                editor.data("last-html", editor.html());
                syncEditorToOriginal(editor, field);
                updateEditorEmptyState(editor);
                refreshReportPreview();
                return;
            }

            if (e.inputType === "insertParagraph") {
                e.preventDefault();

                saveEditorHistory(editor);
                insertLineBreak();

                editor.data("last-html", editor.html());
                syncEditorToOriginal(editor, field);
                updateEditorEmptyState(editor);
                refreshReportPreview();
                return;
            }

            if (e.inputType === "deleteContentBackward" || e.inputType === "deleteContentForward") {
                saveEditorHistory(editor);

                setTimeout(function () {
                    editor.data("last-html", editor.html());
                    syncEditorToOriginal(editor, field);
                    updateEditorEmptyState(editor);
                    refreshReportPreview();
                }, 0);
            }
        });

        editor.on("paste", function (event) {
            event.preventDefault();

            saveEditorHistory(editor);

            let text = "";
            let clipboard = event.originalEvent.clipboardData || window.clipboardData;

            if (clipboard) {
                text = clipboard.getData("text/plain");
            }

            text.split("\n").forEach(function (line, index) {
                if (index > 0) insertLineBreak();
                if (line) insertStyledText(line);
            });

            editor.data("last-html", editor.html());
            syncEditorToOriginal(editor, field);
            updateEditorEmptyState(editor);
            refreshReportPreview();
        });

        editor.on("keyup mouseup input blur", function () {
            syncEditorToOriginal(editor, field);
            updateEditorEmptyState(editor);
            refreshReportPreview();
        });

        return editor;
    }

    function insertTextInsideEditor(editor, field, text) {
        if (!editor || !editor.length) return;

        placeCursorAtEnd(editor[0]);
        saveEditorHistory(editor);

        text.split("\n").forEach(function (line, index) {
            if (index > 0) insertLineBreak();
            if (line) insertStyledText(line);
        });

        editor.data("last-html", editor.html());
        syncEditorToOriginal(editor, field);
        updateEditorEmptyState(editor);
        refreshReportPreview();
    }

    /* =====================================================
       RX PREVIEW CONTAINER FALLBACK
       HTML-e na thakleo JS nijer moto create korbe
    ===================================================== */
    function ensureRxPreviewStructure() {
        if ($("#rxCustomPreview").length) return;

        let rxHtml = `
            <div id="rxCustomPreview" class="rx-prescription-layout d-none">
                <div class="rx-left-column" id="rxLeftColumn"></div>

                <div class="rx-right-column">
                    <div class="rx-symbol-main">℞</div>

                    <div class="rx-medicine-list" id="rxMedicineList"></div>

                    <div class="rx-bottom-section">
                        <div class="rx-bottom-item">
                            <div class="rx-bottom-title">Investigation / Test</div>
                            <div class="rx-bottom-text" id="rxInvestigationText"></div>
                        </div>

                        <div class="rx-bottom-item">
                            <div class="rx-bottom-title">Instructions</div>
                            <div class="rx-bottom-text" id="rxInstructionText"></div>
                        </div>

                        <div class="rx-bottom-item">
                            <div class="rx-bottom-title">Follow Up</div>
                            <div class="rx-bottom-text" id="rxFollowUpText"></div>
                        </div>

                        <div class="rx-signature" id="rxSignatureCustom">
                            <div class="rx-signature-line"></div>
                            Signature
                        </div>
                    </div>
                </div>
            </div>
        `;

        if ($("#rxBodyArea").length) {
            $("#rxBodyArea").prepend(rxHtml);
        } else {
            $("#previewTable").before(rxHtml);
        }
    }

    /* =====================================================
       RX MODE
    ===================================================== */
    function setPrescriptionMode(isPrescription) {
        const report = $("#reportPreview");

        ensureRxPreviewStructure();

        if (isPrescription) {
            report.addClass("rx-mode");

            $("#normalReportLogo").removeClass("d-none");
            $("#rxHeaderBand").addClass("d-none");

            $("#rxCustomPreview").removeClass("d-none");
            $("#previewTable").hide();

            $("#previewTableHeadParam").text("Particular");
            $("#previewTableHeadValue").text("Details");
        } else {
            report.removeClass("rx-mode");

            $("#normalReportLogo").removeClass("d-none");
            $("#rxHeaderBand").addClass("d-none");

            $("#rxCustomPreview").addClass("d-none");
            $("#previewTable").show();

            $("#previewTableHeadParam").text("Meal");
            $("#previewTableHeadValue").text("Food");

            $("#rxLeftColumn").html("");
            $("#rxMedicineList").html("");
            $("#rxInvestigationText").html("");
            $("#rxInstructionText").html("");
            $("#rxFollowUpText").html("");
        }

        refreshReportPreview();
    }

    function buildRegularPrescriptionTemplate() {
        let html = `
            <h4 class="template-title">Regular Prescription</h4>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="C/C" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write chief complaint"></textarea>
            </div>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="O/E" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write examination findings"></textarea>
            </div>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="Diagnosis" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write diagnosis"></textarea>
            </div>

            <div class="template-report-row rx-medicine-row">
                <input type="text" class="template-param-field" value="Rx / Medicine" placeholder="Parameter">

                <div>
                    <div class="rx-builder-panel">
                        <div class="rx-prescription-note">
                            Select medicine, choose simple frequency, add duration, then click Add Medicine.
                        </div>

                        <div class="rx-builder-row">
                            <select class="rx-medicine-select">
                                <option value="">Select Medicine</option>
                                <option value="Tab. Napa 500mg">Tab. Napa 500mg</option>
                                <option value="Tab. Paracetamol 500mg">Tab. Paracetamol 500mg</option>
                                <option value="Tab. Ace 500mg">Tab. Ace 500mg</option>
                                <option value="Cap. Omeprazole 20mg">Cap. Omeprazole 20mg</option>
                                <option value="Tab. Seclo 20mg">Tab. Seclo 20mg</option>
                                <option value="Tab. Sergel 20mg">Tab. Sergel 20mg</option>
                                <option value="Tab. Fexo 120mg">Tab. Fexo 120mg</option>
                                <option value="Tab. Montair 10mg">Tab. Montair 10mg</option>
                                <option value="Tab. Monas 10mg">Tab. Monas 10mg</option>
                                <option value="Syp. Ambroxol">Syp. Ambroxol</option>
                                <option value="ORS Saline">ORS Saline</option>
                                <option value="Tab. Zinc 20mg">Tab. Zinc 20mg</option>
                                <option value="Cap. Doxycycline 100mg">Cap. Doxycycline 100mg</option>
                                <option value="Tab. Azithromycin 500mg">Tab. Azithromycin 500mg</option>
                                <option value="Tab. Cefixime 200mg">Tab. Cefixime 200mg</option>
                            </select>

                            <select class="rx-frequency-select">
                                <option value="">Frequency</option>
                                <option value="Morning">Morning</option>
                                <option value="Noon">Noon</option>
                                <option value="Night">Night</option>
                                <option value="Morning + Night">Morning + Night</option>
                                <option value="Morning + Noon">Morning + Noon</option>
                                <option value="Noon + Night">Noon + Night</option>
                                <option value="Morning + Noon + Night">3 Times Daily</option>
                                <option value="Before Meal">Before Meal</option>
                                <option value="After Meal">After Meal</option>
                                <option value="As Needed">As Needed</option>
                            </select>

                            <input type="text" class="rx-duration-input" placeholder="Duration e.g. 7 days">

                            <button type="button" class="rx-add-medicine-btn">
                                Add Medicine
                            </button>
                        </div>

                        <div class="rx-quick-frequency">
                            <button type="button" data-frequency="Morning">Morning</button>
                            <button type="button" data-frequency="Noon">Noon</button>
                            <button type="button" data-frequency="Night">Night</button>
                            <button type="button" data-frequency="Morning + Night">M + N</button>
                            <button type="button" data-frequency="Morning + Noon + Night">3 Times</button>
                            <button type="button" data-frequency="After Meal">After Meal</button>
                        </div>

                        <textarea class="template-detail-field original-writing-field" placeholder="Medicine list will appear here. You can also write manually."></textarea>
                    </div>
                </div>
            </div>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="Investigation / Test" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write test name or investigation"></textarea>
            </div>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="Instructions" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write instructions or advice"></textarea>
            </div>

            <div class="template-report-row">
                <input type="text" class="template-param-field" value="Follow Up" placeholder="Parameter">
                <textarea class="template-detail-field original-writing-field" placeholder="Write follow-up date or instruction"></textarea>
            </div>
        `;

        $("#reportTemplateArea").html(html);

        $("#reportTemplateArea .template-report-row").each(function () {
            let row = $(this);
            let param = row.find(".template-param-field").val().trim() || "New Field";
            let detailField = row.find(".template-detail-field");

            makeRichEditor(detailField, param);
        });

        refreshReportPreview();
    }

    /* =====================================================
       NORMAL TEMPLATE LOAD / BUILD
    ===================================================== */
    function buildPairedTemplateFromAjaxHtml(html) {
        let temp = $("<div>").html(html);

        let title = temp.find("h1,h2,h3,h4,h5").first().text().trim();

        if (!title) {
            title = $("#reportType option:selected").text() || "Report";
        }

        let fields = temp.find("input[type='text'], textarea");
        let rows = [];

        for (let i = 0; i < fields.length; i += 2) {
            let paramField = $(fields[i]);
            let detailsField = $(fields[i + 1]);

            let paramValue =
                paramField.val() ||
                paramField.attr("placeholder") ||
                paramField.closest(".mb-2,.mb-3,.col,.col-md-6,.col-md-4,.col-md-12").find("label").first().text().trim() ||
                "New Field";

            let detailsPlaceholder =
                detailsField.attr("placeholder") ||
                detailsField.val() ||
                "Write details";

            rows.push({
                param: paramValue,
                placeholder: detailsPlaceholder
            });
        }

        if (rows.length === 0) {
            rows = [
                { param: "Breakfast", placeholder: "Enter Breakfast" },
                { param: "Lunch", placeholder: "Enter Lunch" },
                { param: "Dinner", placeholder: "Enter Dinner" }
            ];
        }

        let cleanHtml = `<h4 class="template-title">${escapeHtml(title)}</h4>`;

        rows.forEach(function (row, index) {
            cleanHtml += `
                <div class="template-report-row" data-template-row="${index}">
                    <input type="text"
                           class="template-param-field"
                           value="${escapeHtml(row.param)}"
                           placeholder="Parameter">

                    <textarea class="template-detail-field original-writing-field"
                              placeholder="${escapeHtml(row.placeholder)}"></textarea>
                </div>
            `;
        });

        $("#reportTemplateArea").html(cleanHtml);

        $("#reportTemplateArea .template-report-row").each(function () {
            let row = $(this);
            let param = row.find(".template-param-field").val().trim() || "New Field";
            let detailField = row.find(".template-detail-field");

            makeRichEditor(detailField, param);
        });

        refreshReportPreview();
    }

    /* =====================================================
       PREVIEW UPDATE
    ===================================================== */
    function getLabelFromField(fieldName) {
        const labels = {
            Date: "Date",
            Name: "Name",
            Age: "Age",
            Gender: "Gender",
            Reason: "Reason",
            ReferredBy: "Referred By",
            BMI: "BMI",
            CauseOfVisit: "Cause Of Visit",
            PhysicalCondition: "Physical Condition",
            PresentMobile: "Present Mobile"
        };

        return labels[fieldName] || fieldName;
    }

    function updateHeaderPreview() {
        $(".header-input").each(function () {
            let fieldName = $(this).data("field");
            let value = $(this).val();
            let label = getLabelFromField(fieldName);

            if (value) {
                $("#previewHeaderFields .header-preview[data-field='" + fieldName + "']")
                    .html(
                        "<span class='preview-label'>" + label + ":</span> " +
                        "<span class='preview-text'></span>"
                    );

                $("#previewHeaderFields .header-preview[data-field='" + fieldName + "']")
                    .find(".preview-text")
                    .text(value);
            } else {
                $("#previewHeaderFields .header-preview[data-field='" + fieldName + "']").html("");
            }
        });
    }

    function rebuildRxPreview() {
        ensureRxPreviewStructure();

        if (!$("#reportPreview").hasClass("rx-mode")) return;

        let leftHtml = "";
        let medicineHtml = "";
        let investigationHtml = "";
        let instructionHtml = "";
        let followUpHtml = "";

        $("#reportTemplateArea .template-report-row").each(function () {
            let row = $(this);
            let label = row.find(".template-param-field").val().trim();
            let editor = row.find(".rich-editor");
            let html = editor.text().trim() ? editor.html() : "";

            if (!label) return;

            let normalized = label.toLowerCase();

            if (
                normalized.includes("rx") ||
                normalized.includes("medicine") ||
                normalized.includes("medication")
            ) {
                medicineHtml = html;
                return;
            }

            if (
                normalized.includes("investigation") ||
                normalized.includes("test")
            ) {
                investigationHtml = html;
                return;
            }

            if (
                normalized.includes("instruction") ||
                normalized.includes("advice")
            ) {
                instructionHtml = html;
                return;
            }

            if (normalized.includes("follow")) {
                followUpHtml = html;
                return;
            }

            leftHtml += `
                <div class="rx-left-item">
                    <div class="rx-left-title">${escapeHtml(label)}</div>
                    <div class="rx-left-text">${html}</div>
                </div>
            `;
        });

        $("#rxLeftColumn").html(leftHtml);
        $("#rxMedicineList").html(medicineHtml);
        $("#rxInvestigationText").html(investigationHtml);
        $("#rxInstructionText").html(instructionHtml);
        $("#rxFollowUpText").html(followUpHtml);
    }

    function rebuildPreviewTable() {
        if ($("#reportPreview").hasClass("rx-mode")) {
            rebuildRxPreview();
            fitReportContentOnePage();
            return;
        }

        let tbody = $("#previewTable tbody");
        tbody.empty();

        $("#reportTemplateArea .template-report-row").each(function () {
            let row = $(this);
            let label = row.find(".template-param-field").val().trim() || "New Field";
            let editor = row.find(".rich-editor");
            let html = editor.text().trim() ? editor.html() : "";

            tbody.append(`
                <tr>
                    <td class="table-field-name">${escapeHtml(label)}</td>
                    <td class="table-field-value">${html}</td>
                </tr>
            `);
        });

        $("#formFields .extra-custom-row").each(function () {
            let row = $(this);
            let label = row.find(".extra-field-name").val().trim() || "New Field";
            let editor = row.find(".rich-editor");
            let html = editor.text().trim() ? editor.html() : "";

            tbody.append(`
                <tr>
                    <td class="table-field-name">${escapeHtml(label)}</td>
                    <td class="table-field-value">${html}</td>
                </tr>
            `);
        });

        fitReportContentOnePage();
    }

    function fitReportContentOnePage() {
        const report = document.getElementById("reportPreview");
        if (!report) return;

        let fontSize = 14;
        document.documentElement.style.setProperty("--detail-font-size", fontSize + "px");

        let guard = 0;

        while (report.scrollHeight > report.clientHeight && fontSize > 4 && guard < 80) {
            fontSize -= 0.5;
            document.documentElement.style.setProperty("--detail-font-size", fontSize + "px");
            guard++;
        }
    }

    function refreshReportPreview() {
        updateHeaderPreview();
        rebuildPreviewTable();
        fitReportContentOnePage();
    }

    function getReportHtml() {
        refreshReportPreview();
        return document.getElementById("reportPreview").outerHTML;
    }

    /* =====================================================
       MODAL / PRINT
    ===================================================== */
    function openPreviewModal() {
        let html = getReportHtml();

        $("#previewModalPaper").html(html);
        updateModalScale();

        let modal = new bootstrap.Modal(document.getElementById("previewModal"));
        modal.show();

        setTimeout(updateModalScale, 200);
    }

    function printReport() {
        let reportHtml = getReportHtml();

        let fontSize = getComputedStyle(document.documentElement)
            .getPropertyValue("--detail-font-size")
            .trim() || "14px";

        let printWindow = window.open("", "_blank", "width=900,height=1200");

        printWindow.document.open();

        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Print Report</title>

                <link rel="stylesheet" href="/static/css/patient_report.css">

                <style>
                    @font-face {
                        font-family: "SutonnyMJ";
                        src: url("/static/fonts/SutonnyMJ.ttf") format("truetype");
                    }

                    :root {
                        --detail-font-size: ${fontSize};
                    }

                    @page {
                        size: A4;
                        margin: 0;
                    }

                    html,
                    body {
                        margin: 0;
                        padding: 0;
                        width: 794px;
                        height: 1123px;
                        background: #ffffff;
                        overflow: hidden;
                        font-family: Arial, Helvetica, sans-serif;
                    }

                    * {
                        box-sizing: border-box;
                        -webkit-print-color-adjust: exact !important;
                        print-color-adjust: exact !important;
                    }

                    #reportPreview {
                        width: 794px !important;
                        height: 1123px !important;
                        min-height: 1123px !important;
                        max-height: 1123px !important;
                        margin: 0 !important;
                        transform: none !important;
                        box-shadow: none !important;
                        border: none !important;
                        overflow: hidden !important;
                    }

                    #reportPreview:not(.rx-mode) {
                        padding: 24px 30px !important;
                    }

                    #reportPreview.rx-mode {
                        padding: 24px 30px !important;
                    }
                </style>
            </head>

            <body>
                ${reportHtml}

                <script>
                    window.onload = function () {
                        setTimeout(function () {
                            window.print();
                        }, 300);
                    };

                    window.onafterprint = function () {
                        window.close();
                    };
                <\/script>
            </body>
            </html>
        `);

        printWindow.document.close();
    }

    /* =====================================================
       PATIENT DATA FETCH
    ===================================================== */
    function fillPatientData(data) {
        console.log("PATIENT DATA:", data);

        setHeaderField("Date", getFirstAvailable(data, [
            "Date",
            "date",
            "created_date",
            "createdAt",
            "created_at"
        ], $("#headerDate").val()));

        setHeaderField("Name", getFirstAvailable(data, [
            "Name",
            "name",
            "patient_name",
            "patientName",
            "full_name",
            "fullName"
        ]));

        setHeaderField("Age", getFirstAvailable(data, [
            "Age",
            "age",
            "patient_age",
            "patientAge"
        ]));

        setHeaderField("Gender", getFirstAvailable(data, [
            "Gender",
            "gender",
            "sex"
        ]));

        setHeaderField("Reason", getFirstAvailable(data, [
            "Reason",
            "reason",
            "reason_to_come",
            "reasonToCome",
            "visit_reason",
            "visitReason"
        ]));

        setHeaderField("ReferredBy", getFirstAvailable(data, [
            "ReferredBy",
            "referred_by",
            "referredBy",
            "referred",
            "reference",
            "ref_by",
            "refBy"
        ]));

        setHeaderField("BMI", getFirstAvailable(data, [
            "BMI",
            "bmi",
            "body_mass_index",
            "bodyMassIndex"
        ]));

        setHeaderField("CauseOfVisit", getFirstAvailable(data, [
            "CauseOfVisit",
            "causeOfVisit",
            "cause_of_visit",
            "Cause_of_visit",
            "cause_of_Visit",
            "cause",
            "Cause",
            "visit_cause",
            "visitCause",
            "chief_complaint",
            "chiefComplaint",
            "complaint",
            "main_problem",
            "mainProblem",
            "problem",
            "Problem",
            "primary_complaint",
            "primaryComplaint"
        ]));

        setHeaderField("PhysicalCondition", getFirstAvailable(data, [
            "PhysicalCondition",
            "physicalCondition",
            "physical_condition",
            "physical",
            "condition",
            "health_condition",
            "healthCondition"
        ]));

        setHeaderField("PresentMobile", getFirstAvailable(data, [
            "PresentMobile",
            "presentMobile",
            "present_mobile",
            "mobile",
            "phone",
            "phone_number",
            "phoneNumber",
            "contact",
            "contact_number",
            "contactNumber"
        ]));

        refreshReportPreview();
    }

    function fetchPatientData(patientId) {
        if (!patientId) return;

        $("#patient_id").val(patientId);

        let url = PATIENT_DATA_URL.replace("__PATIENT_ID__", encodeURIComponent(patientId));

        $.ajax({
            url: url,
            type: "GET",
            success: function (data) {
                fillPatientData(data);
                $("#reportWorkArea").slideDown();
                $("#headerFields").slideDown();
            },
            error: function () {
                alert("Could not fetch patient data.");
            }
        });
    }

    /* =====================================================
       SAVE / OLD PRESCRIPTION
    ===================================================== */
    function savePrescription() {
        refreshReportPreview();

        let patientId = $("#patient_id").val() || $("#PatientSelect").val();

        if (!patientId) {
            alert("Please select a patient first!");
            return;
        }

        let reportOuterHtml = document.getElementById("reportPreview").outerHTML;
        let reportInnerHtml = $("#reportPreview").html();

        $.ajax({
            url: SAVE_URL,
            type: "POST",
            data: {
                html: reportOuterHtml,
                html_content: reportOuterHtml,
                report_html: reportOuterHtml,
                inner_html: reportInnerHtml,
                patient_id: patientId,
                report_type: $("#reportType").val(),
                csrfmiddlewaretoken: $("input[name='csrfmiddlewaretoken']").val()
            },
            success: function () {
                alert("Prescription saved successfully!");
            },
            error: function () {
                alert("Error saving prescription!");
            }
        });
    }

    function goToOldPrescription() {
        let patientId = $("#patient_id").val() || $("#PatientSelect").val();

        if (!patientId) {
            alert("Please select a patient first!");
            return;
        }

        let url = OLD_PRESCRIPTION_URL.replace("__PATIENT_ID__", encodeURIComponent(patientId));
        window.location.href = url;
    }

    /* =====================================================
       EVENTS
    ===================================================== */
    $("#headerFields").hide();

    ensureRxPreviewStructure();
    setDefaultDate();

    let patientIdFromURL = getQueryParam("patient_id");

    if (patientIdFromURL) {
        $("#PatientSelect").val(patientIdFromURL);
        fetchPatientData(patientIdFromURL);
    }

    $("#PatientSelect").on("change", function () {
        let patientId = $(this).val();

        if (!patientId) {
            $("#reportWorkArea").slideUp();
            $("#patient_id").val("");
            return;
        }

        fetchPatientData(patientId);
    });

    $(document).on("input change", ".header-input", refreshReportPreview);

    $("#reportType").off("change").on("change", function () {
        let type = $(this).val();

        if (!type) {
            $("#reportTemplateArea").html("");
            setPrescriptionMode(false);
            rebuildPreviewTable();
            return;
        }

        if (type === "regular_prescription") {
            setPrescriptionMode(true);
            buildRegularPrescriptionTemplate();
            return;
        }

        setPrescriptionMode(false);

        $("#reportTemplateArea").html(`<div class="text-muted p-3">Loading template...</div>`);

        $.ajax({
            url: LOAD_TEMPLATE_URL,
            data: { type: type },
            success: function (html) {
                buildPairedTemplateFromAjaxHtml(html);
                setTimeout(refreshReportPreview, 80);
            },
            error: function () {
                $("#reportTemplateArea").html(`
                    <div class="alert alert-danger">
                        Report template load korte problem hocche.
                    </div>
                `);
            }
        });
    });

    $("#bijoyModeBtn").off("click").on("click", function () {
        if (currentWritingMode === "english") {
            currentWritingMode = "bijoy";

            $("#bijoyModeText").text("Bijoy Classic / SutonnyMJ");
            $("#bijoyModeBtn")
                .removeClass("btn-outline-dark")
                .addClass("btn-dark")
                .text("Disable Bijoy / SutonnyMJ");

        } else {
            currentWritingMode = "english";

            $("#bijoyModeText").text("English / Normal");
            $("#bijoyModeBtn")
                .removeClass("btn-dark")
                .addClass("btn-outline-dark")
                .text("Enable Bijoy / SutonnyMJ");
        }
    });

    $(document).on("input", ".template-param-field", function () {
        let row = $(this).closest(".template-report-row");
        let label = $(this).val().trim() || "New Field";

        row.find(".template-detail-field").attr("data-report-label", label);
        row.find(".rich-editor").attr("data-report-label", label);

        refreshReportPreview();
    });

    $(document).on("click", ".rx-quick-frequency button", function () {
        let frequency = $(this).data("frequency");
        let row = $(this).closest(".rx-medicine-row");

        row.find(".rx-frequency-select").val(frequency);
    });

    $(document).on("click", ".rx-add-medicine-btn", function () {
        let row = $(this).closest(".rx-medicine-row");

        let medicine = row.find(".rx-medicine-select").val();
        let frequency = row.find(".rx-frequency-select").val();
        let duration = row.find(".rx-duration-input").val().trim();

        if (!medicine) {
            alert("Please select a medicine first.");
            return;
        }

        let line = medicine;

        if (frequency) {
            line += "\n" + frequency;
        }

        if (duration) {
            line += "\n" + duration;
        }

        line += "\n";

        let editor = row.find(".rich-editor");
        let field = row.find(".template-detail-field");

        let existingText = editor.text().trim();
        let finalText = existingText ? "\n" + line : line;

        insertTextInsideEditor(editor, field, finalText);

        row.find(".rx-duration-input").val("");
    });

    $("#addFieldBtn").off("click").on("click", function () {
        extraFieldCounter++;

        let fieldId = "field_" + extraFieldCounter;

        let rowHtml = `
            <div class="field-row extra-custom-row" id="${fieldId}" data-extra-row="${extraFieldCounter}">
                <input type="text"
                       class="form-control extra-field-name"
                       placeholder="Field Name"
                       value="New Field">

                <textarea class="extra-field-value original-writing-field"
                          data-report-label="New Field"
                          placeholder="Write details"></textarea>

                <button type="button" class="btn btn-outline-danger btn-sm remove-extra-field">
                    Delete
                </button>
            </div>
        `;

        $("#formFields").append(rowHtml);

        let newField = $("#" + fieldId).find(".extra-field-value");
        makeRichEditor(newField, "New Field");

        refreshReportPreview();
    });

    $(document).on("input", ".extra-field-name", function () {
        let row = $(this).closest(".extra-custom-row");
        let label = $(this).val().trim() || "New Field";

        row.find(".extra-field-value").attr("data-report-label", label);
        row.find(".rich-editor").attr("data-report-label", label);

        refreshReportPreview();
    });

    $(document).on("click", ".remove-extra-field", function () {
        $(this).closest(".extra-custom-row").remove();
        refreshReportPreview();
    });

    $("#previewBtn").on("click", function () {
        refreshReportPreview();
        openPreviewModal();
    });

    $("#printBtn, #modalPrintBtn").on("click", printReport);
    $("#savePrescription, #modalSaveBtn").on("click", savePrescription);
    $("#viewOldPrescription").on("click", goToOldPrescription);

    $("#previewModal").on("shown.bs.modal", updateModalScale);
    $(window).on("resize", updateModalScale);

});