// LINE CHART - ACTIVITY
new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
        labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        datasets: [{
            label: "Activity",
            data: [20, 30, 25, 45, 60, 70, 85],
            borderColor: "#1f8b6b",
            backgroundColor: "rgba(31,139,107,0.1)",
            tension: 0.4,
            fill: true
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false
    }
});

// PIE CHART - BMI
new Chart(document.getElementById("pieChart"), {
    type: "pie",
    data: {
        labels: ["Normal", "Underweight", "Overweight", "Obese"],
        datasets: [{
            data: [40, 15, 30, 15],
            backgroundColor: [
                "#1f8b6b",
                "#7ddc9c",
                "#b6f2c2",
                "#e0f7e9"
            ]
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false
    }
});
