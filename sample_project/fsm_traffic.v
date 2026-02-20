// fsm_traffic.v — Traffic light FSM with bugs
// Bug: No default state in case statement (FSM can get stuck)

module fsm_traffic (
    input  wire clk,
    input  wire rst_n,   // active-low reset
    input  wire sensor,
    output reg  [1:0] light  // 00=RED, 01=GREEN, 10=YELLOW
);

    localparam STATE_RED    = 2'd0;
    localparam STATE_GREEN  = 2'd1;
    localparam STATE_YELLOW = 2'd2;
    // STATE 3 is undefined — no default case below!

    reg [1:0] state, next_state;

    // State register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= STATE_RED;
        else
            state <= next_state;
    end

    // Next state logic — BUG: missing default case
    always @(*) begin
        case (state)
            STATE_RED:    next_state = sensor ? STATE_GREEN : STATE_RED;
            STATE_GREEN:  next_state = STATE_YELLOW;
            STATE_YELLOW: next_state = STATE_RED;
            // Missing: default: next_state = STATE_RED;
        endcase
    end

    // Output logic
    always @(*) begin
        light = state;
    end

endmodule
