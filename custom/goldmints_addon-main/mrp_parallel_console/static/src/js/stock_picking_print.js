/** @odoo-module **/

document.addEventListener('DOMContentLoaded', function() {
    // Setup event listener สำหรับปุ่ม Print ในทุก Picking Form
    document.addEventListener('click', function(e) {
        if (e.target.closest('.action_print_picking')) {
            e.preventDefault();
            e.stopPropagation();
            handlePrintPickingClick();
        }
    });
});

async function handlePrintPickingClick() {
    // ดึง picking ID จากหลายที่
    let pickingId = null;

    // วิธี 1: จาก URL (หลัก)
    // URL format: http://localhost:8811/web#model=stock.picking&id=123&action=...
    const urlHash = window.location.hash;
    const idMatch = urlHash.match(/&id=(\d+)/);
    if (idMatch) {
        pickingId = idMatch[1];
    }

    // วิธี 2: จาก data attribute บน form
    if (!pickingId) {
        const form = document.querySelector('form');
        if (form?.dataset?.id) {
            pickingId = form.dataset.id;
        }
    }

    // วิธี 3: จาก input hidden field
    if (!pickingId) {
        const idInput = document.querySelector('input[name="id"]');
        if (idInput?.value) {
            pickingId = idInput.value;
        }
    }

    if (!pickingId) {
        console.warn("ไม่พบ Picking ID จากทุกแหล่ง", {
            url: window.location.href,
            hash: window.location.hash,
        });
        alert("ไม่สามารถดึง ID ของเบิกได้");
        return;
    }

    console.log("Attempting to print picking:", pickingId);

    try {
        // เรียก action_print_picking ของ stock.picking
        const response = await fetch('/web/dataset/call_kw/stock.picking/action_print_picking', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    model: 'stock.picking',
                    method: 'action_print_picking',
                    args: [[parseInt(pickingId)]],
                    kwargs: {},
                }
            })
        });

        const data = await response.json();
        console.log("Print response:", data);

        if (data.result && data.result.type === 'ir.actions.report') {
            // พิมพ์เอกสาร
            const reportName = data.result.report_name;
            const url = `/report/pdf/${reportName}/${pickingId}`;
            console.log("Opening report URL:", url);
            window.open(url, '_blank');
        } else if (data.error) {
            console.error('Error:', data.error);
            alert('เกิดข้อผิดพลาด: ' + (data.error?.data?.message || data.error.message || 'ไม่ทราบ'));
        } else {
            console.warn('Unexpected response:', data);
            alert('ไม่ได้รับการตอบสนองจาก server');
        }
    } catch (error) {
        console.error('Print error:', error);
        alert('ไม่สามารถพิมพ์เบิกได้: ' + error.message);
    }
}

export default {};


