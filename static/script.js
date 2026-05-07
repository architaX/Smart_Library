// =====================================
// SEARCH FILTER
// =====================================

function searchBooks() {

    let input =
    document.getElementById("searchInput");

    // If search bar doesn't exist
    if(!input){
        return;
    }

    let filter =
    input.value.toLowerCase();

    let rows =
    document.querySelectorAll("table tr");

    rows.forEach((row, index) => {

        // Skip table header
        if(index === 0){
            return;
        }

        let text =
        row.innerText.toLowerCase();

        if(text.includes(filter)){

            row.style.display = "";

        }
        else{

            row.style.display = "none";

        }

    });

}


// =====================================
// CARD HOVER EFFECT
// =====================================

const cards =
document.querySelectorAll(".card");

cards.forEach(card => {

    card.addEventListener("mouseenter", () => {

        card.style.transform =
        "translateY(-8px) scale(1.02)";

    });

    card.addEventListener("mouseleave", () => {

        card.style.transform =
        "translateY(0px) scale(1)";

    });

});


// =====================================
// NOTIFICATION BELL ANIMATION
// =====================================

const bell =
document.querySelector(".notification-bell");

if(bell){

    setInterval(() => {

        bell.classList.toggle("shake");

    }, 2000);

}