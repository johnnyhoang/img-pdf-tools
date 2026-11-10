/**
 * PDF & Image Studio - Main Application Logic
 */

(function () {
    "use strict";

    // Trạng thái ứng dụng
    let pagesData = [];
    let selectedPageIds = new Set();
    let currentPreviewPageId = null;
    let currentEditingPageId = null;
    let editingBaseW = 0;
    let editingBaseH = 0;
    let editingAspectRatio = 1.0;
    let docPageSize = "A4";
    let docOrientation = "portrait";
    let currentScalePct = 100;
    let draggedElement = null;
    let stitchPreviewTimeout = null;
    let estimateSizeTimeout = null;
    let estimatePdfTimeout = null;
    let currentSourcePdf = null;
    let lastFolder = "";

    // Các phần tử DOM chính
    const dom = {
        pageCountText: document.getElementById("pageCountText"),
        lblSelectCount: document.getElementById("lblSelectCount"),
        chkSelectAll: document.getElementById("chkSelectAll"),
        pagesGrid: document.getElementById("pagesGrid"),
        mainDropzone: document.getElementById("mainDropzone"),
        fileInputDrop: document.getElementById("fileInputDrop"),
        fileInputHeader: document.getElementById("fileInputHeader"),
        btnOpenFilesHeader: document.getElementById("btnOpenFilesHeader"),
        btnPickFilesHeader: document.getElementById("btnPickFilesHeader"),
        btnPickFolderHeader: document.getElementById("btnPickFolderHeader"),
        btnHeaderSavePdf: document.getElementById("btnHeaderSavePdf"),
        btnDropzonePickFiles: document.getElementById("btnDropzonePickFiles"),
        btnDropzonePickFolder: document.getElementById("btnDropzonePickFolder"),
        sourcePdfBanner: document.getElementById("sourcePdfBanner"),
        sourcePdfName: document.getElementById("sourcePdfName"),
        sourcePdfFolder: document.getElementById("sourcePdfFolder"),
        btnSavePdfDirect: document.getElementById("btnSavePdfDirect"),
        btnSavePdfAs: document.getElementById("btnSavePdfAs"),
        btnPageSetupDropdown: document.getElementById("btnPageSetupDropdown"),
        lblCurrentPageSize: document.getElementById("lblCurrentPageSize"),
        pageSetupMenu: document.getElementById("pageSetupMenu"),
        docPageSizeButtons: document.getElementById("docPageSizeButtons"),
        btnBatchResize: document.getElementById("btnBatchResize"),
        btnRotateSelected: document.getElementById("btnRotateSelected"),
        btnReverseOrder: document.getElementById("btnReverseOrder"),
        btnBatchFilter: document.getElementById("btnBatchFilter"),
        batchFilterMenu: document.getElementById("batchFilterMenu"),
        btnDeleteSelected: document.getElementById("btnDeleteSelected"),
        btnClearAll: document.getElementById("btnClearAll"),
        
        // Output Tabs
        outputTabs: document.querySelectorAll(".output-tab"),
        tabPanes: document.querySelectorAll(".tab-pane"),

        // Export PDF
        btnExportPdf: document.getElementById("btnExportPdf"),
        pdfFilename: document.getElementById("pdfFilename"),
        btnAiSuggestPdfName: document.getElementById("btnAiSuggestPdfName"),
        pdfNameChips: document.getElementById("pdfNameChips"),
        pdfQuality: document.getElementById("pdfQuality"),
        pdfEstimatedSize: document.getElementById("pdfEstimatedSize"),

        // Stitch
        segLayoutBtns: document.querySelectorAll(".btn-seg-layout"),
        stitchGridSettings: document.getElementById("stitchGridSettings"),
        stitchColsChips: document.getElementById("stitchColsChips"),
        stitchAlignChips: document.getElementById("stitchAlignChips"),
        selStitchSpacing: document.getElementById("selStitchSpacing"),
        selStitchPadding: document.getElementById("selStitchPadding"),
        selStitchBg: document.getElementById("selStitchBg"),
        selStitchFormat: document.getElementById("selStitchFormat"),
        chkStitchBorder: document.getElementById("chkStitchBorder"),
        btnRefreshStitchPreview: document.getElementById("btnRefreshStitchPreview"),
        stitchPreviewImage: document.getElementById("stitchPreviewImage"),
        stitchPlaceholder: document.getElementById("stitchPlaceholder"),
        stitchLoading: document.getElementById("stitchLoading"),
        stitchDimBadge: document.getElementById("stitchDimBadge"),
        btnDownloadStitch: document.getElementById("btnDownloadStitch"),
        btnCopyStitchClipboard: document.getElementById("btnCopyStitchClipboard"),

        // Export ZIP & Compression
        btnExportZip: document.getElementById("btnExportZip"),
        zipQualitySlider: document.getElementById("zipQualitySlider"),
        zipQualityDisplay: document.getElementById("zipQualityDisplay"),
        zipFormat: document.getElementById("zipFormat"),
        zipMaxDim: document.getElementById("zipMaxDim"),
        zipFilename: document.getElementById("zipFilename"),
        btnAiSuggestZipName: document.getElementById("btnAiSuggestZipName"),
        zipNameChips: document.getElementById("zipNameChips"),
        estimateStatus: document.getElementById("estimateStatus"),
        estTotalSize: document.getElementById("estTotalSize"),
        estAvgSize: document.getElementById("estAvgSize"),
        estDim: document.getElementById("estDim"),
        estCount: document.getElementById("estCount"),

        // Modal Page & Image Setup
        cropModal: document.getElementById("cropModal"),
        cropModalTitle: document.getElementById("cropModalTitle"),
        cropModalSubtitle: document.getElementById("cropModalSubtitle"),
        cropCanvas: document.getElementById("cropCanvas"),
        cropCanvasViewport: document.getElementById("cropCanvasViewport"),
        cropMagLens: document.getElementById("cropMagLens"),
        cropMagCanvas: document.getElementById("cropMagCanvas"),
        cropMagLabel: document.getElementById("cropMagLabel"),
        btnAutoDetectCorners: document.getElementById("btnAutoDetectCorners"),
        btnToggleBookSpread: document.getElementById("btnToggleBookSpread"),
        lblToggleBookSpread: document.getElementById("lblToggleBookSpread"),
        btnFullFrameCorners: document.getElementById("btnFullFrameCorners"),
        btnCropLetterFrame: document.getElementById("btnCropLetterFrame"),
        btnCropA4Frame: document.getElementById("btnCropA4Frame"),
        btnTrimShrink: document.getElementById("btnTrimShrink"),
        btnTrimExpand: document.getElementById("btnTrimExpand"),
        btnModalRotateLeft: document.getElementById("btnModalRotateLeft"),
        btnModalRotateRight: document.getElementById("btnModalRotateRight"),
        selModalFilterMode: document.getElementById("selModalFilterMode"),
        rngBrightness: document.getElementById("rngBrightness"),
        valBrightness: document.getElementById("valBrightness"),
        rngContrast: document.getElementById("rngContrast"),
        valContrast: document.getElementById("valContrast"),
        cropNewSizeBadge: document.getElementById("cropNewSizeBadge"),
        pageCanvasChips: document.getElementById("pageCanvasChips"),
        imagePlacementChips: document.getElementById("imagePlacementChips"),
        docTypePresets: document.getElementById("docTypePresets"),
        valResizeScale: document.getElementById("valResizeScale"),
        resizeScaleChips: document.getElementById("resizeScaleChips"),
        rngResizeScale: document.getElementById("rngResizeScale"),
        numResizeW: document.getElementById("numResizeW"),
        numResizeH: document.getElementById("numResizeH"),
        chkLockAspect: document.getElementById("chkLockAspect"),
        btnApplyResize: document.getElementById("btnApplyResize"),
        btnApplyResizeAllSelected: document.getElementById("btnApplyResizeAllSelected"),
        btnCropReset: document.getElementById("btnCropReset"),
        cropModalCloseBtn: document.getElementById("cropModalCloseBtn"),

        // Modal Lightbox
        previewModal: document.getElementById("previewModal"),
        modalPageTitle: document.getElementById("modalPageTitle"),
        modalPageDim: document.getElementById("modalPageDim"),
        modalPageCounter: document.getElementById("modalPageCounter"),
        modalPreviewImg: document.getElementById("modalPreviewImg"),
        modalPrevBtn: document.getElementById("modalPrevBtn"),
        modalNextBtn: document.getElementById("modalNextBtn"),
        modalHeaderPrevBtn: document.getElementById("modalHeaderPrevBtn"),
        modalHeaderNextBtn: document.getElementById("modalHeaderNextBtn"),
        modalOpenCropBtn: document.getElementById("modalOpenCropBtn"),
        modalRotateBtn: document.getElementById("modalRotateBtn"),
        modalDownloadBtn: document.getElementById("modalDownloadBtn"),
        modalCloseBtn: document.getElementById("modalCloseBtn"),
        
        // Toast & Config
        toastContainer: document.getElementById("toastContainer"),
        btnHelp: document.getElementById("btnHelp"),
        helpModal: document.getElementById("helpModal"),
        helpModalCloseBtn: document.getElementById("helpModalCloseBtn"),
        helpModalOkBtn: document.getElementById("helpModalOkBtn"),
        confirmModal: document.getElementById("confirmModal"),
        confirmModalTitle: document.getElementById("confirmModalTitle"),
        confirmModalMessage: document.getElementById("confirmModalMessage"),
        confirmModalOkBtn: document.getElementById("confirmModalOkBtn"),
        confirmModalCancelBtn: document.getElementById("confirmModalCancelBtn"),
        confirmModalCloseBtn: document.getElementById("confirmModalCloseBtn"),
        btnAiConfig: document.getElementById("btnAiConfig"),
        lblConfigStatus: document.getElementById("lblConfigStatus"),
        aiConfigModal: document.getElementById("aiConfigModal"),
        aiConfigModalCloseBtn: document.getElementById("aiConfigModalCloseBtn"),
        btnCancelAiConfig: document.getElementById("btnCancelAiConfig"),
        btnSaveAiConfig: document.getElementById("btnSaveAiConfig"),
        txtOpenAiKey: document.getElementById("txtOpenAiKey"),
        selAiModel: document.getElementById("selAiModel"),
    };

    // Cấu hình tham số ghép ảnh
    let stitchConfig = {
        layout: "grid",
        cols: 3,
        spacing: 24,
        padding: 32,
        bg_color: "#ffffff",
        draw_border: true,
        last_row_align: "center",
        scale: 1.0,
    };

    // ==========================================
    // KHỞI TẠO VÀ SỰ KIỆN BAN ĐẦU
    // ==========================================
    function init() {
        bindEvents();
        fetchPages();
        fetchAiConfigStatus();
        fetchSourceInfo();
    }

    function bindEvents() {
        // Thao tác Hệ thống tệp nhớ thư mục RIÊNG BIỆT (Open / Add / Save)
        if (dom.btnOpenFilesHeader) dom.btnOpenFilesHeader.addEventListener("click", () => handlePickFilesNative("open"));
        if (dom.btnPickFilesHeader) dom.btnPickFilesHeader.addEventListener("click", () => handlePickFilesNative("add"));
        if (dom.btnPickFolderHeader) dom.btnPickFolderHeader.addEventListener("click", () => handlePickFolderNative("open"));
        if (dom.btnDropzonePickFiles) dom.btnDropzonePickFiles.addEventListener("click", () => handlePickFilesNative("open"));
        if (dom.btnDropzonePickFolder) dom.btnDropzonePickFolder.addEventListener("click", () => handlePickFolderNative("open"));
        if (dom.btnHeaderSavePdf) dom.btnHeaderSavePdf.addEventListener("click", handleSavePdfDirect);
        if (dom.btnSavePdfDirect) dom.btnSavePdfDirect.addEventListener("click", handleSavePdfDirect);
        if (dom.btnSavePdfAs) dom.btnSavePdfAs.addEventListener("click", handleSavePdfAs);

        // Nạp tệp tin
        dom.fileInputDrop.addEventListener("change", handleFileSelect);
        dom.fileInputHeader.addEventListener("change", handleFileSelect);

        // Kéo thả file từ ngoài màn hình vào
        window.addEventListener("dragover", (e) => {
            e.preventDefault();
            dom.mainDropzone.classList.add("dragover");
        });
        window.addEventListener("dragleave", (e) => {
            if (e.relatedTarget === null) {
                dom.mainDropzone.classList.remove("dragover");
            }
        });
        window.addEventListener("drop", (e) => {
            e.preventDefault();
            dom.mainDropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                uploadFiles(e.dataTransfer.files);
            }
        });


        // Chọn tất cả
        dom.chkSelectAll.addEventListener("change", (e) => {
            if (e.target.checked) {
                pagesData.forEach(p => selectedPageIds.add(p.id));
            } else {
                selectedPageIds.clear();
            }
            updateSelectionUI();
        });

        // Thiết lập khổ trang tài liệu TOÀN BỘ FILE từ thanh công cụ
        if (dom.btnPageSetupDropdown && dom.pageSetupMenu) {
            dom.btnPageSetupDropdown.addEventListener("click", (e) => {
                e.stopPropagation();
                dom.pageSetupMenu.classList.toggle("show");
            });

            dom.pageSetupMenu.querySelectorAll(".dropdown-item").forEach(item => {
                item.addEventListener("click", () => {
                    const pageSize = item.getAttribute("data-pagesize") || "fit_image";
                    const orientation = item.getAttribute("data-orientation") || "portrait";
                    dom.pageSetupMenu.classList.remove("show");
                    setDocumentPageSize(pageSize, orientation);
                });
            });

            document.addEventListener("click", () => {
                if (dom.pageSetupMenu) dom.pageSetupMenu.classList.remove("show");
            });
        }

        // Thiết lập khổ trang tài liệu TOÀN BỘ FILE từ cụm nút Xuất PDF
        if (dom.docPageSizeButtons) {
            dom.docPageSizeButtons.querySelectorAll(".btn-seg-layout").forEach(btn => {
                btn.addEventListener("click", () => {
                    const pageSize = btn.getAttribute("data-size") || "fit_image";
                    const orientation = btn.getAttribute("data-orient") || "portrait";
                    setDocumentPageSize(pageSize, orientation);
                });
            });
        }

        // Đổi cỡ ảnh hàng loạt cho các trang đã chọn
        dom.btnBatchResize.addEventListener("click", () => {
            if (pagesData.length === 0) return showToast("Chưa có trang nào để chỉnh cỡ.", "info");
            const firstId = selectedPageIds.size > 0 ? Array.from(selectedPageIds)[0] : pagesData[0].id;
            const targetPage = pagesData.find(p => p.id === firstId) || pagesData[0];
            openCropModal(targetPage, true);
        });

        // Xoay các trang đã chọn
        dom.btnRotateSelected.addEventListener("click", () => {
            const targets = selectedPageIds.size > 0 ? Array.from(selectedPageIds) : pagesData.map(p => p.id);
            if (targets.length === 0) return showToast("Chưa có trang nào để xoay.", "info");
            rotatePages(targets, 90);
        });

        // Đảo ngược thứ tự các trang
        dom.btnReverseOrder.addEventListener("click", () => {
            if (pagesData.length < 2) return;
            const reversedIds = [...pagesData].reverse().map(p => p.id);
            reorderPages(reversedIds);
        });

        // Dropdown Bộ lọc hàng loạt
        dom.btnBatchFilter.addEventListener("click", (e) => {
            e.stopPropagation();
            dom.batchFilterMenu.classList.toggle("show");
        });
        document.addEventListener("click", () => {
            dom.batchFilterMenu.classList.remove("show");
        });
        dom.batchFilterMenu.querySelectorAll(".dropdown-item").forEach(item => {
            item.addEventListener("click", (e) => {
                const filter = e.target.getAttribute("data-filter");
                const targets = selectedPageIds.size > 0 ? Array.from(selectedPageIds) : pagesData.map(p => p.id);
                if (targets.length === 0) return showToast("Chưa có trang nào để áp dụng bộ lọc.", "info");
                applyFilter(targets, filter);
            });
        });

        // Xóa các trang đã chọn
        dom.btnDeleteSelected.addEventListener("click", async () => {
            if (selectedPageIds.size === 0) {
                return showToast("Vui lòng chọn ít nhất một trang để xóa.", "info");
            }
            const confirmed = await showConfirmDialog(
                "Xác nhận xóa trang",
                `Bạn có chắc chắn muốn xóa <strong>${selectedPageIds.size} trang</strong> đã chọn? Thao tác này không thể hoàn tác.`,
                { okText: "Xóa trang", isDanger: true }
            );
            if (confirmed) {
                deletePages(Array.from(selectedPageIds));
            }
        });

        // Làm mới tất cả
        dom.btnClearAll.addEventListener("click", async () => {
            if (pagesData.length === 0) return;
            const confirmed = await showConfirmDialog(
                "Làm mới danh sách",
                "Bạn có chắc chắn muốn làm mới toàn bộ danh sách trang? Toàn bộ các trang hiện tại sẽ được xóa để làm lại từ đầu.",
                { okText: "Làm mới", isDanger: true }
            );
            if (confirmed) {
                clearAllPages();
            }
        });

        // Chuyển Tab Xuất Sản Phẩm
        dom.outputTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                dom.outputTabs.forEach(t => t.classList.remove("active"));
                dom.tabPanes.forEach(p => p.classList.remove("active"));
                
                tab.classList.add("active");
                const targetId = tab.getAttribute("data-tab");
                const pane = document.getElementById(targetId);
                if (pane) pane.classList.add("active");

                if (targetId === "tab-stitch") {
                    scheduleStitchPreview(100);
                } else if (targetId === "tab-images") {
                    scheduleEstimateSize(100);
                } else if (targetId === "tab-pdf") {
                    scheduleEstimatePdf(100);
                }
            });
        });

        // XUẤT PDF
        dom.btnExportPdf.addEventListener("click", handleExportPdf);
        dom.pdfQuality.addEventListener("change", () => scheduleEstimatePdf(150));
        dom.btnAiSuggestPdfName.addEventListener("click", () => triggerAiSuggestName(true));

        // GHÉP 1 ẢNH (STITCH)
        dom.segLayoutBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                dom.segLayoutBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                stitchConfig.layout = btn.getAttribute("data-layout");
                dom.stitchGridSettings.style.display = stitchConfig.layout === "grid" ? "block" : "none";
                scheduleStitchPreview();
            });
        });

        dom.stitchColsChips.querySelectorAll(".chip-btn").forEach(chip => {
            chip.addEventListener("click", () => {
                dom.stitchColsChips.querySelectorAll(".chip-btn").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                stitchConfig.cols = parseInt(chip.getAttribute("data-cols"), 10);
                scheduleStitchPreview();
            });
        });

        dom.stitchAlignChips.querySelectorAll(".chip-btn").forEach(chip => {
            chip.addEventListener("click", () => {
                dom.stitchAlignChips.querySelectorAll(".chip-btn").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                stitchConfig.last_row_align = chip.getAttribute("data-align");
                scheduleStitchPreview();
            });
        });

        dom.selStitchSpacing.addEventListener("change", (e) => {
            stitchConfig.spacing = parseInt(e.target.value, 10);
            scheduleStitchPreview();
        });
        dom.selStitchPadding.addEventListener("change", (e) => {
            stitchConfig.padding = parseInt(e.target.value, 10);
            scheduleStitchPreview();
        });
        dom.selStitchBg.addEventListener("change", (e) => {
            stitchConfig.bg_color = e.target.value;
            scheduleStitchPreview();
        });
        dom.chkStitchBorder.addEventListener("change", (e) => {
            stitchConfig.draw_border = e.target.checked;
            scheduleStitchPreview();
        });
        dom.btnRefreshStitchPreview.addEventListener("click", () => scheduleStitchPreview(0));
        dom.btnDownloadStitch.addEventListener("click", handleDownloadStitch);
        dom.btnCopyStitchClipboard.addEventListener("click", handleCopyStitchClipboard);

        // NÉN ẢNH & ƯỚC LƯỢNG KÍCH THƯỚC (TAB 3)
        dom.zipQualitySlider.addEventListener("input", (e) => {
            dom.zipQualityDisplay.textContent = `${e.target.value}%`;
            scheduleEstimateSize(200);
        });
        dom.zipFormat.addEventListener("change", () => scheduleEstimateSize(150));
        dom.zipMaxDim.addEventListener("change", () => scheduleEstimateSize(150));
        dom.btnExportZip.addEventListener("click", handleExportZip);
        dom.btnAiSuggestZipName.addEventListener("click", () => triggerAiSuggestName(true));

        // CẤU HÌNH AI CHATGPT
        dom.btnAiConfig.addEventListener("click", openAiConfigModal);
        dom.aiConfigModalCloseBtn.addEventListener("click", closeAiConfigModal);
        dom.btnCancelAiConfig.addEventListener("click", closeAiConfigModal);
        dom.btnSaveAiConfig.addEventListener("click", saveAiConfig);
        dom.aiConfigModal.addEventListener("click", (e) => {
            if (e.target === dom.aiConfigModal) closeAiConfigModal();
        });

        // MODAL RESIZE & SCALE SỰ KIỆN
        dom.cropModalCloseBtn.addEventListener("click", closeCropModal);
        dom.cropModal.addEventListener("click", (e) => {
            if (e.target === dom.cropModal) closeCropModal();
        });

        // Tự động tính tỷ lệ W <-> H khi gõ số (không bắt người dùng tự tính)
        dom.numResizeW.addEventListener("input", () => {
            const newW = parseInt(dom.numResizeW.value, 10);
            if (!newW || newW <= 0) return;
            if (dom.chkLockAspect && dom.chkLockAspect.checked && editingAspectRatio > 0) {
                const newH = Math.round(newW / editingAspectRatio);
                dom.numResizeH.value = newH;
                const pct = editingBaseW > 0 ? Math.round((newW / editingBaseW) * 100) : 100;
                if (dom.rngResizeScale) dom.rngResizeScale.value = Math.max(15, Math.min(250, pct));
                if (dom.valResizeScale) dom.valResizeScale.textContent = `${pct}%`;
                updateResizeBadge(newW, newH, pct);
            } else {
                updateResizeBadge(newW, parseInt(dom.numResizeH.value, 10) || 0);
            }
        });

        dom.numResizeH.addEventListener("input", () => {
            const newH = parseInt(dom.numResizeH.value, 10);
            if (!newH || newH <= 0) return;
            if (dom.chkLockAspect && dom.chkLockAspect.checked && editingAspectRatio > 0) {
                const newW = Math.round(newH * editingAspectRatio);
                dom.numResizeW.value = newW;
                const pct = editingBaseH > 0 ? Math.round((newH / editingBaseH) * 100) : 100;
                if (dom.rngResizeScale) dom.rngResizeScale.value = Math.max(15, Math.min(250, pct));
                if (dom.valResizeScale) dom.valResizeScale.textContent = `${pct}%`;
                updateResizeBadge(newW, newH, pct);
            } else {
                updateResizeBadge(parseInt(dom.numResizeW.value, 10) || 0, newH);
            }
        });

        // 3 Presets chuẩn theo yêu cầu: Passport, Passport 2 mặt, Card
        if (dom.docTypePresets) {
            dom.docTypePresets.querySelectorAll(".chip-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    const preset = btn.getAttribute("data-preset");
                    applyDocTypePreset(preset);
                });
            });
        }

        // Thanh trượt % Scale
        if (dom.rngResizeScale) {
            dom.rngResizeScale.addEventListener("input", (e) => {
                if (dom.docTypePresets) {
                    dom.docTypePresets.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("active"));
                }
                setScalePercent(parseInt(e.target.value, 10));
            });
        }

        dom.btnApplyResize.addEventListener("click", () => handleApplyResize(false));
        dom.btnApplyResizeAllSelected.addEventListener("click", () => handleApplyResize(true));
        dom.btnCropReset.addEventListener("click", handleResetPage);

        // Các công cụ Chấm góc & Xoay & Chỉnh màu sáng tối trong Modal
        if (dom.btnAutoDetectCorners) dom.btnAutoDetectCorners.addEventListener("click", handleAutoDetectCorners);
        if (dom.btnToggleBookSpread) dom.btnToggleBookSpread.addEventListener("click", handleToggleBookSpread);
        if (dom.btnFullFrameCorners) dom.btnFullFrameCorners.addEventListener("click", handleFullFrameCorners);
        if (dom.btnCropLetterFrame) dom.btnCropLetterFrame.addEventListener("click", () => handleCropFrameRatio("letter"));
        if (dom.btnCropA4Frame) dom.btnCropA4Frame.addEventListener("click", () => handleCropFrameRatio("a4"));
        if (dom.btnTrimShrink) dom.btnTrimShrink.addEventListener("click", () => handleTrimMargin(-0.02));
        if (dom.btnTrimExpand) dom.btnTrimExpand.addEventListener("click", () => handleTrimMargin(0.02));
        if (dom.btnModalRotateLeft) dom.btnModalRotateLeft.addEventListener("click", () => handleModalRotate(-90));
        if (dom.btnModalRotateRight) dom.btnModalRotateRight.addEventListener("click", () => handleModalRotate(90));

        if (dom.selModalFilterMode) {
            dom.selModalFilterMode.addEventListener("change", () => {
                modalFilterMode = dom.selModalFilterMode.value;
                drawCropCanvas();
            });
        }
        if (dom.rngBrightness) {
            dom.rngBrightness.addEventListener("input", (e) => {
                modalBrightness = parseInt(e.target.value, 10);
                if (dom.valBrightness) dom.valBrightness.textContent = (modalBrightness > 0 ? "+" : "") + modalBrightness;
                drawCropCanvas();
            });
        }
        if (dom.rngContrast) {
            dom.rngContrast.addEventListener("input", (e) => {
                modalContrast = parseInt(e.target.value, 10);
                if (dom.valContrast) dom.valContrast.textContent = `${modalContrast}%`;
                drawCropCanvas();
            });
        }

        // Tương tác chuột và cảm ứng trên Canvas chấm góc
        if (dom.cropCanvas) {
            dom.cropCanvas.addEventListener("mousedown", onCanvasPointerDown);
            dom.cropCanvas.addEventListener("mousemove", onCanvasPointerMove);
            window.addEventListener("mouseup", onCanvasPointerUp);

            dom.cropCanvas.addEventListener("touchstart", (e) => {
                onCanvasPointerDown(e);
            }, { passive: false });
            dom.cropCanvas.addEventListener("touchmove", (e) => {
                if (draggingCornerIdx !== -1) e.preventDefault();
                onCanvasPointerMove(e);
            }, { passive: false });
            window.addEventListener("touchend", onCanvasPointerUp);
        }

        // MODAL LIGHTBOX
        dom.modalCloseBtn.addEventListener("click", closeModal);
        dom.previewModal.addEventListener("click", (e) => {
            if (e.target === dom.previewModal) closeModal();
        });
        dom.modalPrevBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            navigateLightbox(-1);
        });
        dom.modalNextBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            navigateLightbox(1);
        });
        dom.modalHeaderPrevBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            navigateLightbox(-1);
        });
        dom.modalHeaderNextBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            navigateLightbox(1);
        });
        dom.modalRotateBtn.addEventListener("click", () => {
            if (currentPreviewPageId) {
                rotatePages([currentPreviewPageId], 90, true);
            }
        });
        dom.modalDownloadBtn.addEventListener("click", () => {
            if (currentPreviewPageId) {
                window.location.href = `/api/export/single/${currentPreviewPageId}`;
            }
        });
        dom.modalOpenCropBtn.addEventListener("click", () => {
            if (currentPreviewPageId) {
                const targetPage = pagesData.find(p => p.id === currentPreviewPageId);
                closeModal();
                if (targetPage) openCropModal(targetPage);
            }
        });

        // Điều hướng bằng bàn phím (Phím mũi tên Trái / Phải, Esc)
        document.addEventListener("keydown", (e) => {
            if (dom.previewModal.style.display !== "none") {
                if (e.key === "ArrowLeft") {
                    e.preventDefault();
                    navigateLightbox(-1);
                } else if (e.key === "ArrowRight") {
                    e.preventDefault();
                    navigateLightbox(1);
                } else if (e.key === "Escape") {
                    closeModal();
                }
            } else if (dom.cropModal.style.display !== "none") {
                if (e.key === "Escape") {
                    closeCropModal();
                }
            }
        });

        // Hướng dẫn
        dom.btnHelp.addEventListener("click", () => {
            dom.helpModal.style.display = "flex";
        });
        dom.helpModalCloseBtn.addEventListener("click", () => {
            dom.helpModal.style.display = "none";
        });
        dom.helpModalOkBtn.addEventListener("click", () => {
            dom.helpModal.style.display = "none";
        });
        dom.helpModal.addEventListener("click", (e) => {
            if (e.target === dom.helpModal) dom.helpModal.style.display = "none";
        });
    }

    // ==========================================
    // XỬ LÝ NẠP FILE & TRUYỀN DỮ LIỆU
    // ==========================================
    function handleFileSelect(e) {
        if (e.target.files && e.target.files.length > 0) {
            uploadFiles(e.target.files);
            e.target.value = "";
        }
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        showToast("Đang nạp và trích xuất tệp tin...", "info");

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();

            if (data.success) {
                showToast(`Đã thêm thành công ${data.uploaded_count} trang tài liệu!`, "success");
                pagesData = data.pages;
                renderPagesGrid();
                await fetchSourceInfo();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(200);
                // Tự động phân tích tên tệp bằng AI
                triggerAiSuggestName(false);
            } else {
                showToast("Không thể tải lên tệp tin.", "error");
            }
        } catch (err) {
            showToast("Có lỗi xảy ra khi nạp tệp tin.", "error");
        }
    }

    async function fetchPages() {
        try {
            const res = await fetch("/api/pages");
            const data = await res.json();
            if (data.success) {
                docPageSize = data.doc_page_size || "fit_image";
                docOrientation = data.doc_orientation || "portrait";
                updateDocPageSizeUI();
                pagesData = data.pages;
                renderPagesGrid();
                if (pagesData.length > 0) {
                    scheduleStitchPreview(200);
                    scheduleEstimateSize(200);
                    scheduleEstimatePdf(200);
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

    // ==========================================
    // RENDER LƯỚI DANH SÁCH TRANG (PAGE GRID)
    // ==========================================
    function renderPagesGrid() {
        dom.pageCountText.textContent = `${pagesData.length} trang`;

        if (pagesData.length === 0) {
            dom.pagesGrid.style.display = "none";
            dom.mainDropzone.style.display = "block";
            dom.stitchPlaceholder.style.display = "flex";
            dom.stitchPreviewImage.style.display = "none";
            dom.stitchDimBadge.textContent = "-- x -- px";
            dom.pdfEstimatedSize.textContent = "-- KB";
            dom.estTotalSize.textContent = "-- KB";
            dom.estAvgSize.textContent = "-- KB";
            dom.estDim.textContent = "-- × -- px";
            dom.estCount.textContent = "0 ảnh";
            selectedPageIds.clear();
            updateSelectionUI();
            return;
        }

        dom.mainDropzone.style.display = "none";
        dom.pagesGrid.style.display = "grid";
        dom.pagesGrid.innerHTML = "";

        pagesData.forEach((page, idx) => {
            const card = document.createElement("div");
            card.className = `page-card ${selectedPageIds.has(page.id) ? "selected" : ""}`;
            card.setAttribute("data-id", page.id);
            card.setAttribute("draggable", "true");

            card.innerHTML = `
                <div class="page-card-header">
                    <div class="page-header-left">
                        <span class="drag-handle" title="Kéo để sắp xếp lại"><i class="fa-solid fa-grip-vertical"></i></span>
                        <span class="page-order-badge">${idx + 1}</span>
                    </div>
                    <label class="chk-container">
                        <input type="checkbox" class="chk-page" ${selectedPageIds.has(page.id) ? "checked" : ""}>
                        <span class="checkmark"></span>
                    </label>
                </div>

                <div class="page-thumb-stage" title="Nhấp để xem ảnh lớn">
                    <img src="/api/pages/${page.id}/thumb?t=${Date.now()}" alt="${escapeHtml(page.name)}" loading="lazy">
                    <div class="page-thumb-overlay">
                        <span><i class="fa-solid fa-magnifying-glass-plus"></i> Xem lớn</span>
                    </div>
                </div>

                <div class="page-card-meta">
                    <span class="page-card-title" title="${escapeHtml(page.name)}">${escapeHtml(page.name)}</span>
                    <div class="page-card-size clickable ${page.is_modified ? 'is-modified' : ''}" title="Chỉnh kích thước">
                        <span><i class="fa-solid fa-up-right-and-down-left-from-center text-accent"></i> ${page.image_width || page.width} × ${page.image_height || page.height} px</span>
                        <i class="fa-solid fa-pen text-muted" style="font-size: 0.65rem;"></i>
                    </div>
                    <select class="page-filter-select" title="Bộ lọc màu & Làm nét">
                        <option value="original" ${page.filter_mode === "original" ? "selected" : ""}>Gốc (Original)</option>
                        <option value="sharp_text" ${page.filter_mode === "sharp_text" ? "selected" : ""}>Làm nét văn bản</option>
                        <option value="clean_bg" ${page.filter_mode === "clean_bg" ? "selected" : ""}>Làm trắng sạch nền</option>
                        <option value="bw_scan" ${page.filter_mode === "bw_scan" ? "selected" : ""}>Quét đen trắng (B&W)</option>
                        <option value="magic_color" ${page.filter_mode === "magic_color" ? "selected" : ""}>Màu tươi (Magic Color)</option>
                        <option value="high_contrast_stamp" ${page.filter_mode === "high_contrast_stamp" ? "selected" : ""}>Nổi bật con dấu</option>
                        <option value="restore_yellowed" ${page.filter_mode === "restore_yellowed" ? "selected" : ""}>Khử ố vàng giấy cũ</option>
                        <option value="remove_bleedthrough" ${page.filter_mode === "remove_bleedthrough" ? "selected" : ""}>Khử mực thấm ngược</option>
                    </select>
                </div>

                <div class="page-card-footer">
                    <div class="btn-group-nav">
                        <button class="btn-card-action btn-move-prev" title="Di chuyển lên trước" ${idx === 0 ? "disabled" : ""}>
                            <i class="fa-solid fa-arrow-left"></i>
                        </button>
                        <button class="btn-card-action btn-move-next" title="Di chuyển về sau" ${idx === pagesData.length - 1 ? "disabled" : ""}>
                            <i class="fa-solid fa-arrow-right"></i>
                        </button>
                    </div>
                    <div class="btn-group-ops">
                        <button class="btn-card-action btn-crop" title="Đổi kích thước & Tỷ lệ ảnh (Resize & Scale)">
                            <i class="fa-solid fa-up-right-and-down-left-from-center text-accent"></i>
                        </button>
                        <button class="btn-card-action btn-rotate" title="Xoay 90°">
                            <i class="fa-solid fa-rotate-right"></i>
                        </button>
                        <button class="btn-card-action btn-dup" title="Nhân bản trang này">
                            <i class="fa-regular fa-copy"></i>
                        </button>
                        <button class="btn-card-action btn-del" title="Xóa trang này">
                            <i class="fa-regular fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            `;

            // Checkbox trang
            const chk = card.querySelector(".chk-page");
            chk.addEventListener("change", (e) => {
                if (e.target.checked) {
                    selectedPageIds.add(page.id);
                    card.classList.add("selected");
                } else {
                    selectedPageIds.delete(page.id);
                    card.classList.remove("selected");
                }
                updateSelectionUI();
                scheduleEstimateSize(150);
                scheduleEstimatePdf(150);
            });

            // Click vào ảnh xem lightbox
            card.querySelector(".page-thumb-stage").addEventListener("click", () => {
                openLightbox(page);
            });

            // Click vào size badge hoặc nút crop để mở modal chỉnh cỡ
            card.querySelector(".page-card-size").addEventListener("click", () => {
                openCropModal(page);
            });
            card.querySelector(".btn-crop").addEventListener("click", () => {
                openCropModal(page);
            });

            // Thay đổi bộ lọc trên thẻ
            card.querySelector(".page-filter-select").addEventListener("change", (e) => {
                applyFilter([page.id], e.target.value);
            });

            // Nút footer
            card.querySelector(".btn-move-prev").addEventListener("click", () => movePage(idx, idx - 1));
            card.querySelector(".btn-move-next").addEventListener("click", () => movePage(idx, idx + 1));
            card.querySelector(".btn-rotate").addEventListener("click", () => rotatePages([page.id], 90));
            card.querySelector(".btn-dup").addEventListener("click", () => duplicatePage(page.id));
            card.querySelector(".btn-del").addEventListener("click", () => deletePages([page.id]));

            // Drag & Drop
            setupDragAndDrop(card);

            dom.pagesGrid.appendChild(card);
        });

        updateSelectionUI();
    }

    function updateSelectionUI() {
        const count = selectedPageIds.size;
        dom.lblSelectCount.textContent = count > 0 ? `Đã chọn (${count})` : "Chọn tất cả";
        dom.chkSelectAll.checked = count > 0 && count === pagesData.length;
        dom.btnBatchResize.textContent = count > 0 ? `Đổi cỡ (${count})` : "Đổi cỡ ảnh";
    }

    // ==========================================
    // KÉO THẢ SẮP XẾP THỨ TỰ (HTML5 D&D)
    // ==========================================
    function setupDragAndDrop(card) {
        card.addEventListener("dragstart", (e) => {
            draggedElement = card;
            card.classList.add("dragging");
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", card.getAttribute("data-id"));
        });

        card.addEventListener("dragend", () => {
            if (draggedElement) {
                draggedElement.classList.remove("dragging");
                draggedElement = null;
            }
        });

        card.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
        });

        card.addEventListener("drop", (e) => {
            e.preventDefault();
            if (!draggedElement || draggedElement === card) return;

            const fromId = draggedElement.getAttribute("data-id");
            const toId = card.getAttribute("data-id");

            const fromIdx = pagesData.findIndex(p => p.id === fromId);
            const toIdx = pagesData.findIndex(p => p.id === toId);

            if (fromIdx !== -1 && toIdx !== -1) {
                const newOrdered = [...pagesData];
                const [movedItem] = newOrdered.splice(fromIdx, 1);
                newOrdered.splice(toIdx, 0, movedItem);

                reorderPages(newOrdered.map(p => p.id));
            }
        });
    }

    function movePage(fromIdx, toIdx) {
        if (toIdx < 0 || toIdx >= pagesData.length) return;
        const newOrdered = [...pagesData];
        const [movedItem] = newOrdered.splice(fromIdx, 1);
        newOrdered.splice(toIdx, 0, movedItem);
        reorderPages(newOrdered.map(p => p.id));
    }

    // ==========================================
    // CÁC THAO TÁC XỬ LÝ TRANG (API CALLS)
    // ==========================================
    async function reorderPages(pageIds) {
        try {
            const res = await fetch("/api/pages/reorder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_ids: pageIds }),
            });
            const data = await res.json();
            if (data.success) {
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
            }
        } catch (e) {
            showToast("Lỗi khi sắp xếp lại trang.", "error");
        }
    }

    async function rotatePages(pageIds, angleDelta = 90, updateModal = false) {
        try {
            const res = await fetch("/api/pages/rotate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_ids: pageIds, angle_delta: angleDelta }),
            });
            const data = await res.json();
            if (data.success) {
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);

                if (updateModal && currentPreviewPageId) {
                    dom.modalPreviewImg.src = `/api/pages/${currentPreviewPageId}/preview?t=${Date.now()}`;
                }
            }
        } catch (e) {
            showToast("Lỗi khi xoay ảnh.", "error");
        }
    }

    async function applyFilter(pageIds, filterMode) {
        showToast("Đang xử lý bộ lọc cho ảnh...", "info");
        try {
            const res = await fetch("/api/pages/enhance", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_ids: pageIds, filter_mode: filterMode }),
            });
            const data = await res.json();
            if (data.success) {
                showToast("Đã áp dụng bộ lọc thành công!", "success");
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
            }
        } catch (e) {
            showToast("Lỗi khi áp dụng bộ lọc.", "error");
        }
    }

    async function deletePages(pageIds) {
        try {
            const res = await fetch("/api/pages/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_ids: pageIds }),
            });
            const data = await res.json();
            if (data.success) {
                pageIds.forEach(id => selectedPageIds.delete(id));
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(200);
                showToast(`Đã xóa ${data.deleted_count} trang.`, "info");
            }
        } catch (e) {
            showToast("Lỗi khi xóa trang.", "error");
        }
    }

    async function duplicatePage(pageId) {
        try {
            const res = await fetch("/api/pages/duplicate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_id: pageId }),
            });
            const data = await res.json();
            if (data.success) {
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(200);
                showToast("Đã nhân bản trang.", "success");
            }
        } catch (e) {
            showToast("Lỗi khi nhân bản trang.", "error");
        }
    }

    async function clearAllPages() {
        try {
            const res = await fetch("/api/pages/clear", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                selectedPageIds.clear();
                pagesData = [];
                renderPagesGrid();
                await fetchSourceInfo();
                showToast("Đã làm mới không gian làm việc.", "info");
            }
        } catch (e) {
            showToast("Lỗi khi làm mới.", "error");
        }
    }

    // ==========================================
    // THIẾT LẬP KHỔ TRANG TÀI LIỆU (DOCUMENT-LEVEL)
    // ==========================================
    async function setDocumentPageSize(pageSize, orientation = "portrait") {
        docPageSize = pageSize;
        docOrientation = orientation;
        updateDocPageSizeUI();

        showToast(`Đang chuyển toàn file sang khổ ${pageSize === 'fit_image' ? 'Vừa khít ảnh' : (orientation === 'landscape' ? 'A4 Ngang' : 'A4 Dọc')}...`, "info");
        try {
            const res = await fetch("/api/document/page-setup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_size: pageSize, orientation: orientation }),
            });
            const data = await res.json();
            if (data.success) {
                pagesData = data.pages;
                renderPagesGrid();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(150);
                showToast(`Đã áp dụng khổ trang cho toàn bộ ${pagesData.length} trang!`, "success");
            }
        } catch (e) {
            showToast("Có lỗi xảy ra khi đổi khổ trang.", "error");
        }
    }

    function updateDocPageSizeUI() {
        let label = "Vừa khít ảnh";
        const normSize = (docPageSize || "").toLowerCase();
        if (normSize === "letter") {
            label = docOrientation === "landscape" ? "Letter Ngang" : "Letter Dọc";
        } else if (normSize === "a4") {
            label = docOrientation === "landscape" ? "A4 Ngang" : "A4 Dọc";
        } else if (docPageSize !== "fit_image") {
            label = `${docPageSize} (${docOrientation === "landscape" ? "Ngang" : "Dọc"})`;
        }
        if (dom.lblCurrentPageSize) dom.lblCurrentPageSize.textContent = `Khổ trang: ${label}`;

        if (dom.pageSetupMenu) {
            dom.pageSetupMenu.querySelectorAll(".dropdown-item").forEach(item => {
                const s = (item.getAttribute("data-pagesize") || "").toLowerCase();
                const o = item.getAttribute("data-orientation") || "portrait";
                const isMatch = (s === normSize) && (s === "fit_image" || o === docOrientation);
                item.classList.toggle("active", isMatch);
            });
        }

        if (dom.docPageSizeButtons) {
            dom.docPageSizeButtons.querySelectorAll(".btn-seg-layout").forEach(btn => {
                const s = (btn.getAttribute("data-size") || "").toLowerCase();
                const o = btn.getAttribute("data-orient") || "portrait";
                const isMatch = (s === normSize) && (s === "fit_image" || o === docOrientation);
                btn.classList.toggle("active", isMatch);
            });
        }
    }

    // ==========================================
    // TRẠNG THÁI MODAL CHỈNH SỬA ẢNH (CANVAS & GÓC & SÁNG TỐI)
    // ==========================================
    let modalOriginalImg = null;
    let modalCorners = null;         // [[x, y], ...] trong hệ tọa độ ảnh gốc
    let modalRotation = 0;           // 0, 90, 180, 270
    let modalBrightness = 0;         // -50 .. +50
    let modalContrast = 0;           // 0 .. 100
    let modalFilterMode = "original";
    let draggingCornerIdx = -1;
    let canvasScale = 1.0;

    const CORNER_LABELS_4 = [
        "Góc trên - trái",
        "Góc trên - phải",
        "Góc dưới - phải",
        "Góc dưới - trái"
    ];

    const CORNER_LABELS_6 = [
        "Góc trên - trái",
        "Gáy trên (giữa)",
        "Góc trên - phải",
        "Góc dưới - phải",
        "Gáy dưới (giữa)",
        "Góc dưới - trái"
    ];

    async function openCropModal(page, isBatchMode = false) {
        currentEditingPageId = page.id;
        currentScalePct = 100;

        editingBaseW = page.image_width || page.width;
        editingBaseH = page.image_height || page.height;
        editingAspectRatio = editingBaseW / Math.max(1, editingBaseH);

        dom.cropModalTitle.innerHTML = isBatchMode && selectedPageIds.size > 0
            ? `<i class="fa-solid fa-wand-magic-sparkles text-accent"></i> Chỉnh sửa ${selectedPageIds.size} ảnh đã chọn`
            : `<i class="fa-solid fa-wand-magic-sparkles text-accent"></i> Chỉnh sửa ảnh: ${escapeHtml(page.name)}`;
        
        dom.cropModalSubtitle.textContent = `Kích thước: ${editingBaseW} × ${editingBaseH} px`;

        // Khởi tạo các thông số chỉnh sửa
        modalRotation = page.rotation || 0;
        modalFilterMode = page.filter_mode || "original";
        modalBrightness = Math.round((page.brightness || 0) * 50);
        modalContrast = Math.round((page.contrast || 0) * 100);

        if (dom.selModalFilterMode) dom.selModalFilterMode.value = modalFilterMode;
        if (dom.rngBrightness) dom.rngBrightness.value = modalBrightness;
        if (dom.valBrightness) dom.valBrightness.textContent = (modalBrightness > 0 ? "+" : "") + modalBrightness;
        if (dom.rngContrast) dom.rngContrast.value = modalContrast;
        if (dom.valContrast) dom.valContrast.textContent = `${modalContrast}%`;

        // Đặt giá trị kích thước hình
        dom.numResizeW.value = editingBaseW;
        dom.numResizeH.value = editingBaseH;
        if (dom.chkLockAspect) dom.chkLockAspect.checked = true;

        if (dom.rngResizeScale) dom.rngResizeScale.value = 100;
        if (dom.valResizeScale) dom.valResizeScale.textContent = "100%";

        if (dom.docTypePresets) {
            dom.docTypePresets.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("active"));
        }

        updateResizeBadge();

        dom.btnApplyResizeAllSelected.style.display = selectedPageIds.size > 1 ? "block" : "none";
        if (selectedPageIds.size > 1) {
            dom.btnApplyResizeAllSelected.textContent = `Áp dụng cho ${selectedPageIds.size} trang đã chọn`;
        }

        dom.cropModal.style.display = "flex";

        // Tải ảnh gốc phục vụ việc chấm góc trên Canvas
        modalOriginalImg = new Image();
        modalOriginalImg.crossOrigin = "anonymous";
        modalOriginalImg.onload = () => {
            const ow = modalOriginalImg.naturalWidth;
            const oh = modalOriginalImg.naturalHeight;
            if (page.corners && (page.corners.length === 4 || page.corners.length === 6)) {
                modalCorners = JSON.parse(JSON.stringify(page.corners));
            } else {
                modalCorners = [
                    [0, 0],
                    [ow - 1, 0],
                    [ow - 1, oh - 1],
                    [0, oh - 1]
                ];
            }
            updateBookSpreadUI();
            drawCropCanvas();
        };
        modalOriginalImg.src = `/api/pages/${page.id}/original?t=${Date.now()}`;
    }

    function closeCropModal() {
        dom.cropModal.style.display = "none";
        if (dom.cropMagLens) dom.cropMagLens.style.display = "none";
        modalOriginalImg = null;
        modalCorners = null;
        currentEditingPageId = null;
        draggingCornerIdx = -1;
    }

    function updateBookSpreadUI() {
        if (!dom.btnToggleBookSpread || !dom.lblToggleBookSpread) return;
        const is6 = modalCorners && modalCorners.length === 6;
        dom.btnToggleBookSpread.classList.toggle("active", is6);
        dom.lblToggleBookSpread.textContent = is6 ? "4 góc đơn" : "2 trang (Gáy giữa)";
    }

    function drawCropCanvas() {
        if (!modalOriginalImg || !dom.cropCanvas || !modalCorners) return;
        const viewport = dom.cropCanvasViewport;
        const vw = Math.max(200, (viewport ? viewport.clientWidth : 600) - 20);
        const vh = Math.max(200, (viewport ? viewport.clientHeight : 440) - 20);

        const nw = modalOriginalImg.naturalWidth || 800;
        const nh = modalOriginalImg.naturalHeight || 600;

        const scale = Math.min(vw / nw, vh / nh, 1.0);
        canvasScale = scale;

        const dispW = Math.max(50, Math.round(nw * scale));
        const dispH = Math.max(50, Math.round(nh * scale));

        const dpr = window.devicePixelRatio || 1;
        dom.cropCanvas.width = dispW * dpr;
        dom.cropCanvas.height = dispH * dpr;
        dom.cropCanvas.style.width = `${dispW}px`;
        dom.cropCanvas.style.height = `${dispH}px`;

        const ctx = dom.cropCanvas.getContext("2d");
        ctx.save();
        ctx.scale(dpr, dpr);

        // 1. Vẽ ảnh gốc (kèm xem trước bộ lọc sáng tối & màu sắc trực quan)
        const bPct = 100 + modalBrightness * 1.0;
        const cPct = 100 + modalContrast * 1.0;
        let filterStr = `brightness(${bPct}%) contrast(${cPct}%)`;
        if (modalFilterMode === "bw_scan") filterStr += " grayscale(100%)";
        else if (modalFilterMode === "clean_bg") filterStr += " brightness(110%)";
        else if (modalFilterMode === "magic_color") filterStr += " saturate(140%)";
        else if (modalFilterMode === "high_contrast_stamp") filterStr += " saturate(160%) contrast(120%)";

        ctx.filter = filterStr;
        ctx.drawImage(modalOriginalImg, 0, 0, dispW, dispH);
        ctx.filter = "none";

        // 2. Chuyển đổi tọa độ các điểm sang hệ Canvas
        const pts = modalCorners.map(([x, y]) => [
            Math.max(0, Math.min(dispW, Math.round(x * scale))),
            Math.max(0, Math.min(dispH, Math.round(y * scale)))
        ]);

        // 3. Phủ màu tối bán trong suốt vùng bên ngoài đa giác (để nổi bật vùng được chọn)
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, 0, dispW, dispH);
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = pts.length - 1; i >= 0; i--) {
            ctx.lineTo(pts[i][0], pts[i][1]);
        }
        ctx.closePath();
        ctx.fillStyle = "rgba(15, 23, 42, 0.55)";
        ctx.fill();
        ctx.restore();

        // 4. Vẽ đường viền đa giác nối các góc
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) {
            ctx.lineTo(pts[i][0], pts[i][1]);
        }
        ctx.closePath();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "#38bdf8";
        ctx.shadowColor = "rgba(0, 0, 0, 0.6)";
        ctx.shadowBlur = 6;
        ctx.stroke();

        // Nếu là 6 điểm (Sách / Hộ chiếu mở đôi): vẽ đường gáy sách giữa (điểm 1 nối điểm 4)
        if (pts.length === 6) {
            ctx.beginPath();
            ctx.setLineDash([6, 6]);
            ctx.strokeStyle = "#f97316";
            ctx.lineWidth = 2.5;
            ctx.moveTo(pts[1][0], pts[1][1]);
            ctx.lineTo(pts[4][0], pts[4][1]);
            ctx.stroke();
        }
        ctx.restore();

        // 5. Vẽ các tay cầm (chấm góc tròn)
        pts.forEach(([px, py], idx) => {
            const isSpine = pts.length === 6 && (idx === 1 || idx === 4);
            const isDragging = (idx === draggingCornerIdx);
            const r = isDragging ? 10 : 7.5;

            ctx.save();
            ctx.beginPath();
            ctx.arc(px, py, r, 0, 2 * Math.PI);
            ctx.fillStyle = "#ffffff";
            ctx.shadowColor = "rgba(0, 0, 0, 0.7)";
            ctx.shadowBlur = 8;
            ctx.fill();

            ctx.lineWidth = isDragging ? 3.5 : 2.5;
            ctx.strokeStyle = isSpine ? "#f97316" : (isDragging ? "#0284c7" : "#38bdf8");
            ctx.stroke();

            // Chấm tâm nhỏ bên trong
            ctx.beginPath();
            ctx.arc(px, py, 2.5, 0, 2 * Math.PI);
            ctx.fillStyle = isSpine ? "#f97316" : "#38bdf8";
            ctx.fill();
            ctx.restore();
        });

        ctx.restore();
    }

    // ==========================================
    // TƯƠNG TÁC KÉO CHẤM GÓC & KÍNH LÚP
    // ==========================================
    function getCanvasCoords(e) {
        if (!dom.cropCanvas) return { x: 0, y: 0, clientX: 0, clientY: 0 };
        const rect = dom.cropCanvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: clientX - rect.left,
            y: clientY - rect.top,
            clientX,
            clientY
        };
    }

    function onCanvasPointerDown(e) {
        if (!modalCorners || !dom.cropCanvas) return;
        const pos = getCanvasCoords(e);
        const hitRadius = 26;

        let bestIdx = -1;
        let minDist = Infinity;

        modalCorners.forEach(([ox, oy], idx) => {
            const cx = ox * canvasScale;
            const cy = oy * canvasScale;
            const d = Math.hypot(cx - pos.x, cy - pos.y);
            if (d <= hitRadius && d < minDist) {
                minDist = d;
                bestIdx = idx;
            }
        });

        if (bestIdx !== -1) {
            draggingCornerIdx = bestIdx;
            showMagnifier(pos.clientX, pos.clientY, bestIdx);
            drawCropCanvas();
        }
    }

    function onCanvasPointerMove(e) {
        if (!modalCorners || !dom.cropCanvas || !modalOriginalImg) return;
        const pos = getCanvasCoords(e);

        if (draggingCornerIdx !== -1) {
            const nw = modalOriginalImg.naturalWidth;
            const nh = modalOriginalImg.naturalHeight;

            // Chuyển đổi tọa độ chuột canvas sang tọa độ pixel ảnh gốc
            const imgX = Math.round(Math.max(-nw * 0.1, Math.min(nw * 1.1, pos.x / canvasScale)));
            const imgY = Math.round(Math.max(-nh * 0.1, Math.min(nh * 1.1, pos.y / canvasScale)));

            modalCorners[draggingCornerIdx] = [imgX, imgY];
            updateMagnifier(pos.clientX, pos.clientY, draggingCornerIdx);
            drawCropCanvas();
        } else {
            // Đổi con trỏ chuột nếu hover gần chấm góc
            let isHover = false;
            modalCorners.forEach(([ox, oy]) => {
                const cx = ox * canvasScale;
                const cy = oy * canvasScale;
                if (Math.hypot(cx - pos.x, cy - pos.y) <= 24) isHover = true;
            });
            dom.cropCanvas.style.cursor = isHover ? "pointer" : "crosshair";
        }
    }

    function onCanvasPointerUp() {
        if (draggingCornerIdx !== -1) {
            draggingCornerIdx = -1;
            hideMagnifier();
            drawCropCanvas();
            updateDimensionsFromCorners();
        }
    }

    function showMagnifier(clientX, clientY, cornerIdx) {
        if (!dom.cropMagLens || !dom.cropMagCanvas || !modalOriginalImg) return;
        dom.cropMagLens.style.display = "block";
        updateMagnifier(clientX, clientY, cornerIdx);
    }

    function updateMagnifier(clientX, clientY, cornerIdx) {
        if (!dom.cropMagLens || !dom.cropMagCanvas || !modalOriginalImg || !modalCorners) return;
        const is6 = modalCorners.length === 6;
        const labels = is6 ? CORNER_LABELS_6 : CORNER_LABELS_4;
        dom.cropMagLabel.textContent = labels[cornerIdx] || "Điểm mốc";

        const vpRect = dom.cropCanvasViewport.getBoundingClientRect();
        const relX = clientX - vpRect.left;
        const relY = clientY - vpRect.top;

        let lensX = relX - 60;
        let lensY = relY - 140;
        if (lensY < 10) lensY = relY + 30;
        if (lensX < 10) lensX = 10;
        if (lensX + 130 > vpRect.width) lensX = vpRect.width - 130;

        dom.cropMagLens.style.left = `${lensX}px`;
        dom.cropMagLens.style.top = `${lensY}px`;

        const ctx = dom.cropMagCanvas.getContext("2d");
        const mw = dom.cropMagCanvas.width;
        const mh = dom.cropMagCanvas.height;
        const zoom = 2.5;
        const sw = mw / zoom;
        const sh = mh / zoom;

        const [ptX, ptY] = modalCorners[cornerIdx];
        ctx.clearRect(0, 0, mw, mh);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";

        ctx.drawImage(
            modalOriginalImg,
            ptX - sw / 2, ptY - sh / 2, sw, sh,
            0, 0, mw, mh
        );

        ctx.strokeStyle = (is6 && (cornerIdx === 1 || cornerIdx === 4)) ? "#f97316" : "#38bdf8";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(mw / 2, 0); ctx.lineTo(mw / 2, mh);
        ctx.moveTo(0, mh / 2); ctx.lineTo(mw, mh / 2);
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(mw / 2, mh / 2, 6, 0, 2 * Math.PI);
        ctx.stroke();
    }

    function hideMagnifier() {
        if (dom.cropMagLens) dom.cropMagLens.style.display = "none";
    }

    function updateDimensionsFromCorners() {
        if (!modalCorners || modalCorners.length < 4) return;
        let w, h;
        if (modalCorners.length === 6) {
            const [tl, tm, tr, br, bm, bl] = modalCorners;
            const topL = Math.hypot(tm[0] - tl[0], tm[1] - tl[1]);
            const botL = Math.hypot(bm[0] - bl[0], bm[1] - bl[1]);
            const topR = Math.hypot(tr[0] - tm[0], tr[1] - tm[1]);
            const botR = Math.hypot(br[0] - bm[0], br[1] - bm[1]);
            w = Math.round(Math.max(topL, botL) + Math.max(topR, botR));
            const hL = Math.hypot(bl[0] - tl[0], bl[1] - tl[1]);
            const hM = Math.hypot(bm[0] - tm[0], bm[1] - tm[1]);
            const hR = Math.hypot(br[0] - tr[0], br[1] - tr[1]);
            h = Math.round(Math.max(hL, hM, hR));
        } else {
            const [tl, tr, br, bl] = modalCorners;
            const w1 = Math.hypot(br[0] - bl[0], br[1] - bl[1]);
            const w2 = Math.hypot(tr[0] - tl[0], tr[1] - tl[1]);
            const h1 = Math.hypot(tr[0] - br[0], tr[1] - br[1]);
            const h2 = Math.hypot(tl[0] - bl[0], tl[1] - bl[1]);
            w = Math.round(Math.max(w1, w2));
            h = Math.round(Math.max(h1, h2));
        }
        if (w > 20 && h > 20) {
            editingBaseW = w;
            editingBaseH = h;
            editingAspectRatio = w / h;
            dom.numResizeW.value = Math.round(w * (currentScalePct / 100));
            dom.numResizeH.value = Math.round(h * (currentScalePct / 100));
            updateResizeBadge();
        }
    }

    // ==========================================
    // CÁC THAO TÁC THANH CÔNG CỤ TRONG MODAL
    // ==========================================
    async function handleAutoDetectCorners() {
        if (!currentEditingPageId) return;
        showToast("Đang tự động nhận diện góc mép giấy...", "info");
        try {
            const res = await fetch(`/api/pages/${currentEditingPageId}/auto-detect-corners`, { method: "POST" });
            const data = await res.json();
            if (data.success && data.corners) {
                modalCorners = data.corners;
                updateBookSpreadUI();
                drawCropCanvas();
                updateDimensionsFromCorners();
                showToast(data.detected ? "Đã nhận diện chuẩn 4 góc mép tài liệu!" : "Đã căn trọn trang tài liệu.", "success");
            }
        } catch (e) {
            showToast("Lỗi khi nhận diện góc mép giấy.", "error");
        }
    }

    function handleToggleBookSpread() {
        if (!modalCorners || !modalOriginalImg) return;
        if (modalCorners.length === 6) {
            modalCorners = [modalCorners[0], modalCorners[2], modalCorners[3], modalCorners[5]];
            showToast("Đã chuyển về 4 góc đơn trang.", "info");
        } else {
            const [tl, tr, br, bl] = modalCorners;
            const tm = [Math.round((tl[0] + tr[0]) / 2), Math.round((tl[1] + tr[1]) / 2)];
            const bm = [Math.round((bl[0] + br[0]) / 2), Math.round((bl[1] + br[1]) / 2)];
            modalCorners = [tl, tm, tr, br, bm, bl];
            showToast("Đã thêm 2 điểm gáy giữa cho sách / hộ chiếu mở đôi.", "info");
        }
        updateBookSpreadUI();
        drawCropCanvas();
        updateDimensionsFromCorners();
    }

    function handleFullFrameCorners() {
        if (!modalOriginalImg) return;
        const w = modalOriginalImg.naturalWidth;
        const h = modalOriginalImg.naturalHeight;
        if (modalCorners && modalCorners.length === 6) {
            modalCorners = [
                [0, 0],
                [Math.round(w / 2), 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [Math.round(w / 2), h - 1],
                [0, h - 1]
            ];
        } else {
            modalCorners = [
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1]
            ];
        }
        drawCropCanvas();
        updateDimensionsFromCorners();
        showToast("Đã đặt góc bao trọn toàn bộ ảnh.", "info");
    }

    function handleCropFrameRatio(type = "letter") {
        if (!modalOriginalImg) return;
        const w = modalOriginalImg.naturalWidth;
        const h = modalOriginalImg.naturalHeight;
        if (!w || !h) return;

        const isHorizontal = w >= h;
        let targetRatio;
        let label;
        if (type === "letter") {
            // US Letter: 8.5 x 11 inches (1700 x 2200 px @ 200 DPI)
            targetRatio = isHorizontal ? (11.0 / 8.5) : (8.5 / 11.0);
            label = "US Letter (8.5 × 11\")";
        } else {
            // A4: 210 x 297 mm (1654 x 2339 px @ 200 DPI)
            targetRatio = isHorizontal ? (297.0 / 210.0) : (210.0 / 297.0);
            label = "A4 (210 × 297 mm)";
        }

        const currentRatio = w / h;
        let cropW, cropH;
        if (currentRatio > targetRatio) {
            cropH = h;
            cropW = Math.round(h * targetRatio);
        } else {
            cropW = w;
            cropH = Math.round(w / targetRatio);
        }

        const x0 = Math.max(0, Math.round((w - cropW) / 2));
        const y0 = Math.max(0, Math.round((h - cropH) / 2));
        const x1 = Math.min(w - 1, x0 + cropW);
        const y1 = Math.min(h - 1, y0 + cropH);

        modalCorners = [
            [x0, y0],
            [x1, y0],
            [x1, y1],
            [x0, y1]
        ];

        updateBookSpreadUI();
        drawCropCanvas();
        updateDimensionsFromCorners();
        showToast(`Đã căn 4 góc cắt chuẩn tỷ lệ ${label}!`, "success");
    }

    function handleTrimMargin(marginFactor) {
        if (!modalCorners) return;
        const cx = modalCorners.reduce((s, p) => s + p[0], 0) / modalCorners.length;
        const cy = modalCorners.reduce((s, p) => s + p[1], 0) / modalCorners.length;
        const scale = 1.0 + marginFactor;
        modalCorners = modalCorners.map(([x, y]) => [
            Math.round(cx + (x - cx) * scale),
            Math.round(cy + (y - cy) * scale)
        ]);
        drawCropCanvas();
        updateDimensionsFromCorners();
        showToast(marginFactor > 0 ? "Đã giãn lề +2%." : "Đã thu lề -2%.", "info");
    }

    function handleModalRotate(angleDelta) {
        modalRotation = (modalRotation + angleDelta + 360) % 360;
        showToast(`Đã xoay góc ${modalRotation}°.`, "info");
        drawCropCanvas();
    }

    function updateResizeBadge() {
        if (!dom.cropNewSizeBadge) return;
        const curW = parseInt(dom.numResizeW.value, 10) || editingBaseW;
        const curH = parseInt(dom.numResizeH.value, 10) || editingBaseH;
        dom.cropNewSizeBadge.innerHTML = `Hình ảnh: <strong>${curW} × ${curH} px (${currentScalePct}%)</strong>`;
    }

    function setScalePercent(pct) {
        pct = Math.max(10, Math.min(300, parseInt(pct, 10) || 100));
        currentScalePct = pct;
        const newW = Math.round(editingBaseW * (pct / 100));
        const newH = Math.round(editingBaseH * (pct / 100));
        dom.numResizeW.value = newW;
        dom.numResizeH.value = newH;
        if (dom.rngResizeScale) dom.rngResizeScale.value = pct;
        if (dom.valResizeScale) dom.valResizeScale.textContent = `${pct}%`;
        updateResizeBadge();
    }

    function applyDocTypePreset(preset) {
        if (!editingBaseW || !editingBaseH) return;
        const isHorizontal = editingBaseW >= editingBaseH;
        let targetW, targetH;

        if (preset === "letter_fill") {
            // US Letter (8.5 x 11 inches = 1700 x 2200 px @ 200 DPI)
            // FILL: Phóng to lấp đầy toàn bộ khổ giấy, không chừa viền trắng
            const sheetW = isHorizontal ? 2200 : 1700;
            const sheetH = isHorizontal ? 1700 : 2200;
            if (dom.chkLockAspect && dom.chkLockAspect.checked) {
                const scale = Math.max(sheetW / editingBaseW, sheetH / editingBaseH);
                targetW = Math.round(editingBaseW * scale);
                targetH = Math.round(editingBaseH * scale);
            } else {
                targetW = sheetW;
                targetH = sheetH;
            }
        } else if (preset === "letter_fit") {
            // FIT: Co vừa vặn trọn vẹn trong khổ US Letter
            const sheetW = isHorizontal ? 2200 : 1700;
            const sheetH = isHorizontal ? 1700 : 2200;
            if (dom.chkLockAspect && dom.chkLockAspect.checked) {
                const scale = Math.min(sheetW / editingBaseW, sheetH / editingBaseH);
                targetW = Math.round(editingBaseW * scale);
                targetH = Math.round(editingBaseH * scale);
            } else {
                targetW = sheetW;
                targetH = sheetH;
            }
        } else if (preset === "a4_fill") {
            // A4: 1654 x 2339 px @ 200 DPI
            // FILL: Phóng to lấp đầy toàn bộ khổ A4
            const sheetW = isHorizontal ? 2339 : 1654;
            const sheetH = isHorizontal ? 1654 : 2339;
            if (dom.chkLockAspect && dom.chkLockAspect.checked) {
                const scale = Math.max(sheetW / editingBaseW, sheetH / editingBaseH);
                targetW = Math.round(editingBaseW * scale);
                targetH = Math.round(editingBaseH * scale);
            } else {
                targetW = sheetW;
                targetH = sheetH;
            }
        } else if (preset === "a4_fit") {
            // FIT: Co vừa vặn trọn vẹn trong khổ A4
            const sheetW = isHorizontal ? 2339 : 1654;
            const sheetH = isHorizontal ? 1654 : 2339;
            if (dom.chkLockAspect && dom.chkLockAspect.checked) {
                const scale = Math.min(sheetW / editingBaseW, sheetH / editingBaseH);
                targetW = Math.round(editingBaseW * scale);
                targetH = Math.round(editingBaseH * scale);
            } else {
                targetW = sheetW;
                targetH = sheetH;
            }
        } else if (preset === "passport") {
            // Passport 88 x 125 mm (~693 x 984 px @ 200 DPI)
            if (isHorizontal) {
                targetH = 693;
                targetW = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetH * editingAspectRatio) : 984;
            } else {
                targetW = 693;
                targetH = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetW / editingAspectRatio) : 984;
            }
        } else if (preset === "passport_double") {
            // Passport 2 mặt mở 176 x 125 mm (~1386 x 984 px @ 200 DPI)
            if (isHorizontal) {
                targetW = 1386;
                targetH = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetW / editingAspectRatio) : 984;
            } else {
                targetH = 1386;
                targetW = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetH * editingAspectRatio) : 984;
            }
        } else if (preset === "card") {
            // Thẻ ID / CCCD 86 x 54 mm (~674 x 425 px @ 200 DPI)
            if (isHorizontal) {
                targetW = 674;
                targetH = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetW / editingAspectRatio) : 425;
            } else {
                targetH = 674;
                targetW = (dom.chkLockAspect && dom.chkLockAspect.checked) ? Math.round(targetH * editingAspectRatio) : 425;
            }
        }

        if (targetW && targetH) {
            dom.numResizeW.value = targetW;
            dom.numResizeH.value = targetH;
            const pct = Math.round((targetW / editingBaseW) * 100);
            currentScalePct = pct;
            if (dom.rngResizeScale) dom.rngResizeScale.value = Math.max(15, Math.min(250, pct));
            if (dom.valResizeScale) dom.valResizeScale.textContent = `${pct}%`;
            if (dom.docTypePresets) {
                dom.docTypePresets.querySelectorAll(".chip-btn").forEach(b => {
                    b.classList.toggle("active", b.getAttribute("data-preset") === preset);
                });
            }
            updateResizeBadge();
        }
    }

    async function handleApplyResize(isAllSelected = false) {
        if (!currentEditingPageId) return;

        const targetW = parseInt(dom.numResizeW.value, 10);
        const targetH = parseInt(dom.numResizeH.value, 10);

        if (!targetW || targetW <= 0 || !targetH || targetH <= 0) {
            return showToast("Kích thước hình không hợp lệ.", "error");
        }

        showToast("Đang lưu chỉnh sửa hình ảnh...", "info");

        try {
            const res = await fetch(`/api/pages/${currentEditingPageId}/edit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    corners: modalCorners,
                    rotation: modalRotation,
                    brightness: modalBrightness / 50.0,
                    contrast: modalContrast / 100.0,
                    filter_mode: dom.selModalFilterMode ? dom.selModalFilterMode.value : "original",
                    width: targetW,
                    height: targetH,
                    image_scale: 1.0,
                    apply_to_selected: isAllSelected,
                    selected_page_ids: Array.from(selectedPageIds)
                }),
            });

            const data = await res.json();
            if (res.ok && data.success) {
                showToast("Đã lưu chỉnh sửa hình ảnh thành công!", "success");
                pagesData = data.pages;
                renderPagesGrid();
                closeCropModal();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(200);
            } else {
                showToast(data.detail || "Lỗi khi lưu chỉnh sửa.", "error");
            }
        } catch (e) {
            showToast("Có lỗi xảy ra khi lưu thiết lập.", "error");
        }
    }

    async function handleResetPage() {
        if (!currentEditingPageId) return;
        const confirmed = await showConfirmDialog(
            "Khôi phục ảnh gốc",
            "Bạn có chắc chắn muốn khôi phục ảnh gốc nguyên bản ban đầu? Mọi chỉnh sửa chấm góc, cắt lề, xoay, chỉnh màu sáng tối và kích thước sẽ được đặt lại.",
            { okText: "Khôi phục", isDanger: false }
        );
        if (!confirmed) return;

        try {
            const res = await fetch("/api/pages/reset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ page_id: currentEditingPageId }),
            });
            const data = await res.json();
            if (data.success) {
                showToast("Đã khôi phục ảnh gốc ban đầu!", "success");
                pagesData = data.pages;
                renderPagesGrid();
                closeCropModal();
                scheduleStitchPreview(300);
                scheduleEstimateSize(200);
                scheduleEstimatePdf(200);
            }
        } catch (e) {
            showToast("Lỗi khi khôi phục.", "error");
        }
    }

    // ==========================================
    // ƯỚC LƯỢNG KÍCH THƯỚC & NÉN ẢNH THỜI GIAN THỰC
    // ==========================================
    function scheduleEstimateSize(delay = 250) {
        clearTimeout(estimateSizeTimeout);
        estimateSizeTimeout = setTimeout(fetchEstimateSize, delay);
    }

    async function fetchEstimateSize() {
        if (pagesData.length === 0) return;

        dom.estimateStatus.textContent = "Đang ước tính...";
        const targetIds = selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null;
        const quality = parseInt(dom.zipQualitySlider.value, 10) || 85;
        const format = dom.zipFormat.value || "jpeg";
        const maxDim = parseInt(dom.zipMaxDim.value, 10) || null;

        try {
            const res = await fetch("/api/estimate-size", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    page_ids: targetIds,
                    format: format,
                    quality: quality,
                    max_dimension: maxDim,
                }),
            });
            const data = await res.json();
            if (data.success) {
                dom.estTotalSize.textContent = data.formatted_total;
                dom.estAvgSize.textContent = data.formatted_avg;
                dom.estDim.textContent = `${data.sample_width} × ${data.sample_height} px`;
                dom.estCount.textContent = `${data.count} ảnh`;
                dom.estimateStatus.textContent = "Cập nhật tức thì";
            }
        } catch (e) {
            dom.estimateStatus.textContent = "Lỗi tính toán";
        }
    }

    function scheduleEstimatePdf(delay = 300) {
        clearTimeout(estimatePdfTimeout);
        estimatePdfTimeout = setTimeout(fetchEstimatePdf, delay);
    }

    function getActiveLayoutMode() {
        if (docPageSize === "fit_image") return "original";
        const normSize = (docPageSize || "").toLowerCase();
        if (normSize === "letter") {
            return docOrientation === "landscape" ? "uniform_letter_landscape" : "uniform_letter_portrait";
        }
        return docOrientation === "landscape" ? "uniform_a4_landscape" : "uniform_a4_portrait";
    }

    async function fetchEstimatePdf() {
        if (pagesData.length === 0) return;

        const layoutMode = getActiveLayoutMode();
        const quality = parseInt(dom.pdfQuality.value, 10) || 85;
        const targetIds = selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null;

        try {
            const res = await fetch("/api/estimate-pdf-size", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    page_ids: targetIds,
                    layout_mode: layoutMode,
                    quality: quality,
                }),
            });
            const data = await res.json();
            if (data.success) {
                dom.pdfEstimatedSize.textContent = data.formatted_total;
            }
        } catch (e) {
            console.error(e);
        }
    }

    // ==========================================
    // XUẤT FILE PDF HOÀN CHỈNH (ĐỒNG NHẤT KHỔ TRANG)
    // ==========================================
    async function handleExportPdf() {
        if (pagesData.length === 0) {
            return showToast("Chưa có trang nào để xuất PDF.", "error");
        }

        const layoutMode = getActiveLayoutMode();
        const quality = parseInt(dom.pdfQuality.value, 10) || 85;
        const filename = (dom.pdfFilename.value.trim() || "tai_lieu_dong_nhat") + ".pdf";

        const originalBtnText = dom.btnExportPdf.innerHTML;
        dom.btnExportPdf.disabled = true;
        dom.btnExportPdf.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang đóng gói PDF đồng nhất...';

        try {
            const res = await fetch("/api/export/pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    page_ids: selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null,
                    layout_mode: layoutMode,
                    quality: quality,
                    filename: filename,
                }),
            });

            if (!res.ok) throw new Error("Xuất PDF thất bại.");

            const blob = await res.blob();
            downloadBlob(blob, filename);
            showToast("Đã tạo và tải file PDF với kích thước trang đồng nhất thành công!", "success");
        } catch (err) {
            showToast("Lỗi khi tạo file PDF.", "error");
        } finally {
            dom.btnExportPdf.disabled = false;
            dom.btnExportPdf.innerHTML = originalBtnText;
        }
    }

    // ==========================================
    // QUẢN LÝ THƯ MỤC NHỚ & LƯU FILE PDF GỐC (FS MANAGER)
    // ==========================================
    async function fetchSourceInfo() {
        try {
            const res = await fetch("/api/fs/source-info");
            const data = await res.json();
            if (data.success) {
                lastFolder = data.last_folder || "";
                currentSourcePdf = data.source_pdf;
                updateSourcePdfUI();
            }
        } catch (e) {
            console.error("fetchSourceInfo error", e);
        }
    }

    function updateSourcePdfUI() {
        if (currentSourcePdf && currentSourcePdf.path) {
            if (dom.sourcePdfBanner) dom.sourcePdfBanner.style.display = "flex";
            if (dom.sourcePdfName) dom.sourcePdfName.textContent = currentSourcePdf.name || "";
            if (dom.sourcePdfFolder) dom.sourcePdfFolder.textContent = currentSourcePdf.folder || "";
            if (dom.btnHeaderSavePdf) {
                dom.btnHeaderSavePdf.style.display = "inline-flex";
                dom.btnHeaderSavePdf.title = `Lưu trực tiếp vào: ${currentSourcePdf.name} (có sao lưu an toàn .bak)`;
            }
            if (dom.pdfFilename && (!dom.pdfFilename.value || dom.pdfFilename.value === "tai_lieu_dong_nhat")) {
                const base = currentSourcePdf.name.replace(/\.pdf$/i, "");
                dom.pdfFilename.value = base;
            }
        } else {
            if (dom.sourcePdfBanner) dom.sourcePdfBanner.style.display = "none";
            if (dom.btnHeaderSavePdf) dom.btnHeaderSavePdf.style.display = "none";
        }
    }

    async function handlePickFilesNative(action = "open") {
        const actionLabel = action === "add" ? "thêm tệp" : "mở tệp";
        showToast(`Đang mở hộp thoại ${actionLabel}...`, "info");
        try {
            const res = await fetch(`/api/fs/pick-files?action=${encodeURIComponent(action)}`, { method: "POST" });
            const data = await res.json();
            if (data.cancelled) return;
            if (data.success) {
                pagesData = data.pages || [];
                renderPagesGrid();
                await fetchSourceInfo();
                if (data.uploaded_count > 0) {
                    showToast(`Đã ${action === 'add' ? 'thêm' : 'nạp'} thành công ${data.uploaded_count} trang!`, "success");
                    scheduleStitchPreview(300);
                    scheduleEstimateSize(200);
                    scheduleEstimatePdf(200);
                    triggerAiSuggestName(false);
                }
            } else {
                if (dom.fileInputDrop) dom.fileInputDrop.click();
            }
        } catch (err) {
            console.warn("Native file picker failed, falling back to browser file input:", err);
            if (dom.fileInputDrop) dom.fileInputDrop.click();
        }
    }

    async function handlePickFolderNative(action = "open") {
        showToast("Đang mở hộp thoại chọn thư mục...", "info");
        try {
            const res = await fetch(`/api/fs/pick-folder?action=${encodeURIComponent(action)}`, { method: "POST" });
            const data = await res.json();
            if (data.cancelled) return;
            if (data.success) {
                pagesData = data.pages || [];
                renderPagesGrid();
                await fetchSourceInfo();
                if (data.uploaded_count > 0) {
                    showToast(`Đã nạp ${data.uploaded_count} trang từ thư mục: ${data.folder}`, "success");
                    scheduleStitchPreview(300);
                    scheduleEstimateSize(200);
                    scheduleEstimatePdf(200);
                    triggerAiSuggestName(false);
                } else {
                    showToast("Không tìm thấy ảnh hoặc file PDF trong thư mục đã chọn.", "info");
                }
            } else {
                showToast("Không thể mở thư mục.", "error");
            }
        } catch (err) {
            showToast("Có lỗi xảy ra khi chọn thư mục.", "error");
        }
    }

    async function handleSavePdfDirect() {
        if (!currentSourcePdf || !currentSourcePdf.path) {
            return showToast("Chưa có file PDF gốc để lưu đè.", "info");
        }
        if (pagesData.length === 0) {
            return showToast("Chưa có trang nào để lưu.", "error");
        }

        const confirmed = await showConfirmDialog(
            "Xác nhận lưu đè file PDF gốc",
            `Bạn có chắc chắn muốn lưu đè vào file gốc:<br><strong style="color:var(--accent); word-break: break-all;">${escapeHtml(currentSourcePdf.name)}</strong>?<br><span style="font-size:0.8rem;color:#64748b;display:block;margin-top:8px;"><i class="fa-solid fa-shield-halved" style="color:#16a34a;margin-right:4px;"></i> Hệ thống sẽ tự động tạo file sao lưu an toàn (<code>.bak</code>) trước khi lưu.</span>`,
            { okText: "Lưu đè file gốc", isDanger: false }
        );
        if (!confirmed) return;

        const layoutMode = getActiveLayoutMode();
        const quality = parseInt(dom.pdfQuality.value, 10) || 85;

        showToast("Đang xử lý và lưu đè file PDF...", "info");

        try {
            const res = await fetch("/api/fs/save-pdf-direct", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    layout_mode: layoutMode,
                    quality: quality,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Lỗi máy chủ (${res.status})`);
            }

            const data = await res.json();
            if (data.success) {
                const sizeKb = Math.round(data.size_bytes / 1024);
                showToast(`Đã lưu đè file PDF thành công (${sizeKb} KB)!`, "success");
                await fetchSourceInfo();
            }
        } catch (e) {
            showToast("Lỗi khi lưu đè PDF: " + (e.message || ""), "error");
        }
    }

    async function handleSavePdfAs() {
        if (pagesData.length === 0) {
            return showToast("Chưa có trang nào để lưu.", "error");
        }

        const layoutMode = getActiveLayoutMode();
        const quality = parseInt(dom.pdfQuality.value, 10) || 85;
        const filename = (dom.pdfFilename.value.trim() || "tai_lieu_dong_nhat") + ".pdf";

        showToast("Đang mở hộp thoại lưu tệp...", "info");

        try {
            const res = await fetch("/api/fs/save-pdf-as", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    suggested_name: filename,
                    layout_mode: layoutMode,
                    quality: quality,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Lỗi máy chủ (${res.status})`);
            }

            const data = await res.json();
            if (data.cancelled) return;
            if (data.success) {
                const sizeKb = Math.round(data.size_bytes / 1024);
                showToast(`Đã lưu PDF vào ổ đĩa: ${data.filename} (${sizeKb} KB)!`, "success");
                await fetchSourceInfo();
            }
        } catch (e) {
            showToast("Lỗi khi lưu PDF: " + (e.message || ""), "error");
        }
    }

    // ==========================================
    // GHÉP 1 ẢNH (PDF & IMAGE STITCHER)
    // ==========================================
    function scheduleStitchPreview(delay = 400) {
        if (pagesData.length === 0) return;
        clearTimeout(stitchPreviewTimeout);
        stitchPreviewTimeout = setTimeout(fetchStitchPreview, delay);
    }

    async function fetchStitchPreview() {
        if (pagesData.length === 0) return;

        dom.stitchLoading.style.display = "flex";
        dom.stitchPlaceholder.style.display = "none";

        try {
            const res = await fetch("/api/export/stitch-preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...stitchConfig,
                    page_ids: selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null,
                }),
            });

            if (!res.ok) throw new Error("Lỗi kết xuất ảnh ghép.");

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            dom.stitchPreviewImage.src = url;
            dom.stitchPreviewImage.style.display = "block";

            const outW = res.headers.get("X-Out-Width") || "--";
            const outH = res.headers.get("X-Out-Height") || "--";
            dom.stitchDimBadge.textContent = `${outW} × ${outH} px`;
        } catch (e) {
            console.error(e);
        } finally {
            dom.stitchLoading.style.display = "none";
        }
    }

    async function handleDownloadStitch() {
        if (pagesData.length === 0) {
            return showToast("Chưa có trang nào để ghép ảnh.", "error");
        }

        const fmt = dom.selStitchFormat.value || "jpeg";
        const ext = fmt === "png" ? "png" : "jpg";
        const filename = `anh_ghep_${pagesData.length}_trang.${ext}`;

        const origText = dom.btnDownloadStitch.innerHTML;
        dom.btnDownloadStitch.disabled = true;
        dom.btnDownloadStitch.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xuất...';

        try {
            const reqBody = {
                ...stitchConfig,
                page_ids: selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null,
                format: fmt,
                quality: 92,
                filename: filename,
            };

            const res = await fetch("/api/export/stitch-download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqBody),
            });

            if (!res.ok) throw new Error("Lỗi khi tải ảnh ghép.");

            const blob = await res.blob();
            downloadBlob(blob, filename);
            showToast("Đã tải ảnh ghép thành công!", "success");
        } catch (e) {
            showToast("Lỗi khi xuất ảnh ghép.", "error");
        } finally {
            dom.btnDownloadStitch.disabled = false;
            dom.btnDownloadStitch.innerHTML = origText;
        }
    }

    async function handleCopyStitchClipboard() {
        if (pagesData.length === 0) return;

        try {
            showToast("Đang chuẩn bị ảnh sao chép...", "info");
            const res = await fetch("/api/export/stitch-download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...stitchConfig,
                    page_ids: selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null,
                    format: "png",
                    quality: 90,
                }),
            });

            const blob = await res.blob();
            await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
            showToast("Đã sao chép ảnh ghép vào Clipboard!", "success");
        } catch (err) {
            showToast("Không thể sao chép tự động (Trình duyệt hạn chế sao chép ảnh).", "error");
        }
    }

    // ==========================================
    // XUẤT DANH SÁCH ẢNH (ZIP & NÉN)
    // ==========================================
    async function handleExportZip() {
        if (pagesData.length === 0) {
            return showToast("Chưa có trang nào để xuất gói ảnh ZIP.", "error");
        }

        const fmt = dom.zipFormat.value || "jpeg";
        const quality = parseInt(dom.zipQualitySlider.value, 10) || 85;
        const maxDim = parseInt(dom.zipMaxDim.value, 10) || null;
        const filename = (dom.zipFilename.value.trim() || "danh_sach_anh_da_nen") + ".zip";

        const origText = dom.btnExportZip.innerHTML;
        dom.btnExportZip.disabled = true;
        dom.btnExportZip.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nén ZIP...';

        try {
            const res = await fetch("/api/export/images-zip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    page_ids: selectedPageIds.size > 0 ? Array.from(selectedPageIds) : null,
                    format: fmt,
                    quality: quality,
                    max_dimension: maxDim,
                    filename: filename,
                }),
            });

            if (!res.ok) throw new Error("Lỗi nén tệp tin ZIP.");

            const blob = await res.blob();
            downloadBlob(blob, filename);
            showToast("Đã tải về tệp tin ZIP các trang ảnh nén thành công!", "success");
        } catch (e) {
            showToast("Lỗi khi xuất tệp tin ZIP.", "error");
        } finally {
            dom.btnExportZip.disabled = false;
            dom.btnExportZip.innerHTML = origText;
        }
    }

    // ==========================================
    // MODAL LIGHTBOX XEM CHI TIẾT
    // ==========================================
    function openLightbox(page) {
        if (!page) return;
        currentPreviewPageId = page.id;
        const idx = pagesData.findIndex(p => p.id === page.id);
        updateLightboxUI(page, idx >= 0 ? idx : 0);
        dom.previewModal.style.display = "flex";
    }

    function updateLightboxUI(page, idx) {
        if (!page) return;
        currentPreviewPageId = page.id;
        dom.modalPageTitle.textContent = page.name || "Tài liệu";
        dom.modalPageDim.textContent = `${page.width} × ${page.height} px`;
        if (dom.modalPageCounter) {
            dom.modalPageCounter.textContent = `Trang ${idx + 1} / ${pagesData.length}`;
        }

        // Hiệu ứng chuyển mượt và tải trước ảnh mới
        dom.modalPreviewImg.style.opacity = "0.4";
        dom.modalPreviewImg.style.transition = "opacity 0.15s ease";
        const tempImg = new Image();
        tempImg.onload = () => {
            dom.modalPreviewImg.src = tempImg.src;
            dom.modalPreviewImg.style.opacity = "1";
        };
        tempImg.onerror = () => {
            dom.modalPreviewImg.style.opacity = "1";
        };
        tempImg.src = `/api/pages/${page.id}/preview?t=${Date.now()}`;

        const hasPrev = idx > 0;
        const hasNext = idx < pagesData.length - 1;

        if (dom.modalPrevBtn) dom.modalPrevBtn.disabled = !hasPrev;
        if (dom.modalNextBtn) dom.modalNextBtn.disabled = !hasNext;
        if (dom.modalHeaderPrevBtn) dom.modalHeaderPrevBtn.disabled = !hasPrev;
        if (dom.modalHeaderNextBtn) dom.modalHeaderNextBtn.disabled = !hasNext;
    }

    function navigateLightbox(direction) {
        if (!pagesData || pagesData.length === 0) return;
        let currentIdx = pagesData.findIndex(p => p.id === currentPreviewPageId);
        if (currentIdx === -1) currentIdx = 0;

        const nextIdx = currentIdx + direction;
        if (nextIdx >= 0 && nextIdx < pagesData.length) {
            const targetPage = pagesData[nextIdx];
            currentPreviewPageId = targetPage.id;
            updateLightboxUI(targetPage, nextIdx);
        }
    }

    function closeModal() {
        dom.previewModal.style.display = "none";
        dom.modalPreviewImg.src = "";
        currentPreviewPageId = null;
    }

    // ==========================================
    // TIỆN ÍCH CHUNG
    // ==========================================
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-triangle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
        dom.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
            toast.style.transition = "all 0.25s ease";
            setTimeout(() => toast.remove(), 250);
        }, 3000);
    }

    // ==========================================
    // AI GỢI Ý TÊN FILE & CẤU HÌNH CHATGPT
    // ==========================================
    async function triggerAiSuggestName(isUserAction = true) {
        if (!pagesData || pagesData.length === 0) {
            await fetchPages();
        }
        if (!pagesData || pagesData.length === 0) {
            if (isUserAction) showToast("Vui lòng nạp ít nhất 1 trang tài liệu.", "info");
            return;
        }

        const btns = [dom.btnAiSuggestPdfName, dom.btnAiSuggestZipName].filter(Boolean);
        btns.forEach(b => {
            b.disabled = true;
            b.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Đang phân tích...</span>';
        });

        if (isUserAction) {
            showToast("AI đang đọc tài liệu để gợi ý tên file chuẩn...", "info");
        }

        try {
            const res = await fetch("/api/ai/suggest-name", { method: "POST" });
            if (!res.ok) throw new Error(`Lỗi máy chủ (${res.status})`);
            const data = await res.json();
            if (data.success && data.primary) {
                // Cập nhật tên vào input
                if (dom.pdfFilename) dom.pdfFilename.value = data.primary;
                if (dom.zipFilename) dom.zipFilename.value = data.primary;

                // Render danh sách gợi ý dạng chips
                renderNameChips(dom.pdfNameChips, data.suggestions || [data.primary], dom.pdfFilename);
                renderNameChips(dom.zipNameChips, data.suggestions || [data.primary], dom.zipFilename);

                if (isUserAction) {
                    const msg = data.engine === "chatgpt"
                        ? `AI đã gợi ý: ${data.primary} (${data.message})`
                        : `Đã gợi ý tên: ${data.primary}`;
                    showToast(msg, "success");
                }
            } else {
                if (isUserAction) showToast(data.message || "Không thể gợi ý tên lúc này.", "info");
            }
        } catch (e) {
            if (isUserAction) showToast("Lỗi khi kết nối AI: " + (e.message || ""), "error");
        } finally {
            btns.forEach(b => {
                b.disabled = false;
                b.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles text-accent"></i> <span>AI Gợi ý tên</span>';
            });
        }
    }

    function renderNameChips(container, suggestions, targetInput) {
        if (!container) return;
        container.innerHTML = "";
        if (!suggestions || suggestions.length <= 1) {
            container.style.display = "none";
            return;
        }

        container.style.display = "flex";
        suggestions.forEach(name => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = `name-chip ${targetInput.value === name ? "active" : ""}`;
            chip.innerHTML = `<i class="fa-regular fa-file"></i> <span>${escapeHtml(name)}</span>`;
            chip.addEventListener("click", () => {
                targetInput.value = name;
                container.querySelectorAll(".name-chip").forEach(c => c.classList.remove("active"));
                chip.classList.add("active");
                showToast(`Đã chọn tên: ${name}`, "info");
            });
            container.appendChild(chip);
        });
    }

    async function fetchAiConfigStatus() {
        try {
            const res = await fetch("/api/config");
            const data = await res.json();
            if (data.success) {
                if (data.has_openai_key) {
                    dom.lblConfigStatus.innerHTML = '<span style="color:#22c55e;">●</span> AI Key (Đã bật)';
                    if (dom.txtOpenAiKey) dom.txtOpenAiKey.placeholder = `Đã lưu key (${data.masked_key})`;
                } else {
                    dom.lblConfigStatus.innerHTML = 'ChatGPT Key';
                    if (dom.txtOpenAiKey) dom.txtOpenAiKey.placeholder = 'sk-proj-...';
                }
                if (dom.selAiModel && data.model) {
                    dom.selAiModel.value = data.model;
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

    function openAiConfigModal() {
        dom.aiConfigModal.style.display = "flex";
    }

    function closeAiConfigModal() {
        dom.aiConfigModal.style.display = "none";
    }

    async function saveAiConfig() {
        const apiKey = dom.txtOpenAiKey.value.trim();
        const model = dom.selAiModel.value || "gpt-4o-mini";

        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    openai_api_key: apiKey ? apiKey : undefined,
                    openai_model: model,
                }),
            });
            const data = await res.json();
            if (data.success) {
                showToast("Đã lưu cấu hình AI ChatGPT thành công!", "success");
                closeAiConfigModal();
                fetchAiConfigStatus();
            } else {
                showToast("Lỗi khi lưu cấu hình.", "error");
            }
        } catch (e) {
            showToast("Có lỗi xảy ra khi lưu cấu hình.", "error");
        }
    }

    // ==========================================
    // DIALOG XÁC NHẬN RIÊNG (CUSTOM IN-APP DIALOG)
    // ==========================================
    function showConfirmDialog(title, message, options = {}) {
        return new Promise((resolve) => {
            const okText = options.okText || "Xác nhận";
            const cancelText = options.cancelText || "Hủy bỏ";
            const isDanger = options.isDanger !== false;

            dom.confirmModalTitle.innerHTML = isDanger
                ? `<i class="fa-solid fa-triangle-exclamation text-danger mr-1"></i> ${escapeHtml(title)}`
                : `<i class="fa-solid fa-circle-question text-accent mr-1"></i> ${escapeHtml(title)}`;

            dom.confirmModalMessage.innerHTML = message;
            dom.confirmModalOkBtn.textContent = okText;
            dom.confirmModalOkBtn.className = `btn ${isDanger ? 'btn-danger' : 'btn-primary'}`;
            dom.confirmModalCancelBtn.textContent = cancelText;

            const cleanup = (result) => {
                dom.confirmModal.style.display = "none";
                dom.confirmModalOkBtn.removeEventListener("click", onOk);
                dom.confirmModalCancelBtn.removeEventListener("click", onCancel);
                dom.confirmModalCloseBtn.removeEventListener("click", onCancel);
                dom.confirmModal.removeEventListener("click", onBackdrop);
                resolve(result);
            };

            const onOk = () => cleanup(true);
            const onCancel = () => cleanup(false);
            const onBackdrop = (e) => {
                if (e.target === dom.confirmModal) cleanup(false);
            };

            dom.confirmModalOkBtn.addEventListener("click", onOk);
            dom.confirmModalCancelBtn.addEventListener("click", onCancel);
            dom.confirmModalCloseBtn.addEventListener("click", onCancel);
            dom.confirmModal.addEventListener("click", onBackdrop);

            dom.confirmModal.style.display = "flex";
        });
    }

    function escapeHtml(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Khởi động
    document.addEventListener("DOMContentLoaded", init);
})();
