// counter.v — Sample module with intentional bugs for FABB demo
// Bug 1: Missing posedge qualifier (line 18)
// Bug 2: Reset polarity mismatch (line 20)
// Bug 3: Off-by-one in comparison (line 25)

module counter #(parameter N = 8) (
    input  wire        clk,
    input  wire        rst,       // active-high reset
    input  wire        en,
    output reg  [N-1:0] count_out,
    output reg         overflow
);

    localparam MAX_COUNT = 255;

    // BUG 1: Should be "always @(posedge clk)" not "always @(clk)"
    always @(clk) begin
        // BUG 2: Reset polarity — should be if (rst) not if (!rst)
        if (!rst) begin
            count_out <= 0;
            overflow  <= 0;
        end else if (en) begin
            // BUG 3: Off-by-one — should be >= MAX_COUNT not > MAX_COUNT
            if (count_out > MAX_COUNT) begin
                count_out <= 0;
                overflow  <= 1;
            end else begin
                count_out <= count_out + 1;
                overflow  <= 0;
            end
        end
    end

endmodule
